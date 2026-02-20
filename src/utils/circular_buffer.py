"""Thread-safe circular buffer for audio streaming."""

import queue
import threading
from typing import Optional, TypeVar

import numpy as np

T = TypeVar("T")


class CircularBuffer:
    """Thread-safe circular buffer using a bounded queue.

    Supports concurrent producer (audio capture) and consumer (pipeline)
    threads. Drops oldest items when the buffer is full to prevent
    unbounded memory growth during slow processing.
    """

    def __init__(self, capacity: int = 32) -> None:
        """Initialize CircularBuffer.

        Args:
            capacity: Maximum number of items in the buffer.
                      When full, the oldest item is dropped.
        """
        if capacity <= 0:
            raise ValueError(f"capacity must be > 0, got {capacity}")
        self.capacity = capacity
        self._queue: queue.Queue = queue.Queue(maxsize=capacity)
        self._lock = threading.Lock()
        self._dropped = 0

    def put(self, item: object, block: bool = False) -> bool:
        """Put an item into the buffer.

        If the buffer is full and block=False, the oldest item is
        silently dropped to make room.

        Args:
            item: Item to add.
            block: If True, block until space is available.

        Returns:
            True if the item was added, False if an old item was dropped.
        """
        try:
            self._queue.put(item, block=block)
            return True
        except queue.Full:
            with self._lock:
                try:
                    self._queue.get_nowait()
                    self._dropped += 1
                except queue.Empty:
                    pass
            try:
                self._queue.put_nowait(item)
            except queue.Full:
                pass
            return False

    def get(self, timeout: Optional[float] = None) -> Optional[object]:
        """Get the next item from the buffer.

        Args:
            timeout: Seconds to wait before returning None. None = blocking.

        Returns:
            Next item or None on timeout.
        """
        try:
            if timeout is not None:
                return self._queue.get(timeout=timeout)
            return self._queue.get_nowait()
        except queue.Empty:
            return None

    def clear(self) -> None:
        """Remove all items from the buffer."""
        with self._lock:
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    break

    @property
    def size(self) -> int:
        """Return the current number of items in the buffer."""
        return self._queue.qsize()

    @property
    def is_empty(self) -> bool:
        """Return True if the buffer is empty."""
        return self._queue.empty()

    @property
    def is_full(self) -> bool:
        """Return True if the buffer is full."""
        return self._queue.full()

    @property
    def dropped_count(self) -> int:
        """Return the number of items dropped due to buffer overflow."""
        return self._dropped
