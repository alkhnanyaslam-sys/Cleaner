"""
services/queue_manager.py
A simple asyncio-based job queue with a fixed number of workers
(config.MAX_WORKERS), so heavy Demucs jobs never run unbounded in parallel
and never block the bot's event loop from receiving new messages/commands.
"""
import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Callable, Awaitable, Any, Dict

from config import config
from utils.logger import logger


@dataclass
class Job:
    job_id: str
    user_id: int
    coro_factory: Callable[[], Awaitable[Any]]
    status_callback: Callable[[str], Awaitable[None]] = None


class QueueManager:
    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers or config.MAX_WORKERS
        self._queue: asyncio.Queue[Job] = asyncio.Queue()
        self._workers_started = False
        self._active_per_user: Dict[int, int] = {}

    def user_active_count(self, user_id: int) -> int:
        return self._active_per_user.get(user_id, 0)

    async def submit(self, user_id: int, coro_factory, status_callback=None) -> str:
        job_id = uuid.uuid4().hex[:12]
        job = Job(job_id=job_id, user_id=user_id, coro_factory=coro_factory,
                   status_callback=status_callback)
        self._active_per_user[user_id] = self._active_per_user.get(user_id, 0) + 1
        await self._queue.put(job)
        return job_id

    def start_workers(self):
        if self._workers_started:
            return
        self._workers_started = True
        for i in range(self.max_workers):
            asyncio.create_task(self._worker_loop(i))

    async def _worker_loop(self, worker_index: int):
        while True:
            job = await self._queue.get()
            try:
                if job.status_callback:
                    await job.status_callback("processing")
                await job.coro_factory()
            except Exception:
                logger.exception(f"Job {job.job_id} failed in worker {worker_index}")
                if job.status_callback:
                    try:
                        await job.status_callback("failed")
                    except Exception:
                        pass
            finally:
                count = self._active_per_user.get(job.user_id, 1)
                self._active_per_user[job.user_id] = max(0, count - 1)
                self._queue.task_done()


queue_manager = QueueManager()
