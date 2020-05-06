"""
Non blocking logging file handler by using threads.
"""

from threading import Thread
from logging import FileHandler

from queue import Queue


class NonBlockingFileHandler(FileHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._queue = Queue(maxsize=9999)
        self._thread = Thread(target=self.__loop, daemon=True)
        self._thread.start()

    def emit(self, record):
        self._queue.put(record)

    def __loop(self):
        while True:
            record = self._queue.get()
            try:
                super().emit(record)
            except Exception as e:
                print("Async handler exception:", e)
