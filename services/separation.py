"""
services/separation.py
Wraps Demucs for AI-based vocal/instrumental separation.
The model is loaded once and reused (not reloaded per request).
Designed so the model can be swapped by changing config.MODEL_NAME only.
"""
import asyncio
import os
import time
from typing import Tuple

from utils.logger import logger
from utils.system_info import get_device

_model_cache = {}
_load_lock = asyncio.Lock()


async def _get_model(model_name: str):
    """
    Loads the Demucs model once and caches it in memory.
    Uses a lock so concurrent requests don't trigger double-loading.
    """
    if model_name in _model_cache:
        return _model_cache[model_name]

    async with _load_lock:
        if model_name in _model_cache:
            return _model_cache[model_name]

        def _load():
            from demucs.pretrained import get_model
            model = get_model(model_name)
            device = get_device()
            model.to(device)
            model.eval()
            return model

        loop = asyncio.get_event_loop()
        logger.info(f"Loading Demucs model '{model_name}'...")
        model = await loop.run_in_executor(None, _load)
        _model_cache[model_name] = model
        logger.info("Model loaded.")
        return model


async def separate(input_wav_path: str, output_dir: str, model_name: str) -> Tuple[str, str, float]:
    """
    Runs source separation on input_wav_path.
    Returns (vocals_path, instrumental_path, processing_time_seconds).
    """
    os.makedirs(output_dir, exist_ok=True)
    model = await _get_model(model_name)

    def _run_separation():
        import torch
        import torchaudio
        from demucs.apply import apply_model

        device = get_device()
        wav, sr = torchaudio.load(input_wav_path)
        wav = wav.to(device)

        # Demucs expects a batch dimension
        ref = wav.mean(0)
        wav_norm = (wav - ref.mean()) / ref.std()

        with torch.no_grad():
            sources = apply_model(
                model, wav_norm[None], device=device,
                progress=False, split=True,
            )[0]

        sources = sources * ref.std() + ref.mean()

        source_names = model.sources  # e.g. ['drums', 'bass', 'other', 'vocals']
        vocals_idx = source_names.index("vocals")

        vocals = sources[vocals_idx].cpu()
        instrumental = sum(
            sources[i] for i in range(len(source_names)) if i != vocals_idx
        ).cpu()

        vocals_path = os.path.join(output_dir, "vocals.wav")
        instrumental_path = os.path.join(output_dir, "instrumental.wav")

        torchaudio.save(vocals_path, vocals, sr)
        torchaudio.save(instrumental_path, instrumental, sr)

        return vocals_path, instrumental_path

    start = time.time()
    loop = asyncio.get_event_loop()
    try:
        vocals_path, instrumental_path = await loop.run_in_executor(None, _run_separation)
    except Exception as e:
        logger.error(f"Separation failed: {type(e).__name__}")
        raise
    elapsed = time.time() - start
    return vocals_path, instrumental_path, elapsed
