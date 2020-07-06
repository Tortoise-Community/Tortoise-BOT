import asyncio
from typing import Any
from datetime import datetime, timezone, timedelta


class CoolDown:
    def __init__(self, seconds: float):
        if seconds < 1:
            raise ValueError("Cooldown has to be positive.")
        self._cool_down_seconds = timedelta(seconds=seconds)
        self._cool_downs = {}
        self._loop_running = True

    def add_to_cool_down(self, key: Any, *, seconds: int = None):
        if seconds is None:
            seconds = self._cool_down_seconds
        self._cool_downs[key] = self._get_current_datetime() + seconds

    def is_on_cool_down(self, key: Any) -> bool:
        return key in self._cool_downs

    def retry_after(self, key: Any) -> float:
        difference: timedelta = self._cool_downs[key] - self._get_current_datetime()
        return difference.seconds

    @classmethod
    def _get_current_datetime(cls) -> datetime:
        return datetime.now(timezone.utc)

    async def start(self):
        while self._loop_running:
            to_delete = []
            for key, date in self._cool_downs.items():
                if self._get_current_datetime() > date:
                    to_delete.append(key)

            for key in to_delete:
                del self._cool_downs[key]

            await asyncio.sleep(1)
