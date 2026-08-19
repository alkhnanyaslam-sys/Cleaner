"""
utils/system_info.py
Reports CPU / RAM / GPU status for the admin panel.
"""
import psutil

try:
    import torch
    _TORCH_AVAILABLE = True
except ImportError:
    _TORCH_AVAILABLE = False


def get_device() -> str:
    """Auto-detect the best available device for Demucs."""
    if _TORCH_AVAILABLE and torch.cuda.is_available():
        return "cuda"
    return "cpu"


def get_system_status() -> dict:
    cpu_percent = psutil.cpu_percent(interval=0.3)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage(".")

    gpu_info = "غير متوفر"
    if _TORCH_AVAILABLE and torch.cuda.is_available():
        try:
            name = torch.cuda.get_device_name(0)
            allocated = torch.cuda.memory_allocated(0) / (1024 ** 2)
            total = torch.cuda.get_device_properties(0).total_memory / (1024 ** 2)
            gpu_info = f"{name} | {allocated:.0f}MB / {total:.0f}MB"
        except Exception:
            gpu_info = "GPU موجود لكن تعذر قراءة التفاصيل"

    return {
        "cpu_percent": cpu_percent,
        "ram_percent": mem.percent,
        "ram_used_mb": mem.used / (1024 ** 2),
        "ram_total_mb": mem.total / (1024 ** 2),
        "disk_used_gb": disk.used / (1024 ** 3),
        "disk_total_gb": disk.total / (1024 ** 3),
        "gpu": gpu_info,
        "device": get_device(),
    }
