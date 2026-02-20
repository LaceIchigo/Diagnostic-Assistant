"""Real-time audio capture using sounddevice with callback-based input."""

import threading
from typing import Optional, Callable

import numpy as np

from utils.circular_buffer import CircularBuffer
from utils.logger import get_logger

logger = get_logger(__name__)


class AudioCapture:
    """Captures audio from a microphone in real-time using a circular buffer.

    Uses sounddevice's callback mechanism to continuously read audio chunks
    and write them into a thread-safe circular buffer for downstream processing.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        dtype: str = "float32",
        device_index: Optional[int] = None,
        chunk_duration: float = 1.5,
        buffer_size: int = 32,
        on_chunk: Optional[Callable[[np.ndarray], None]] = None,
    ) -> None:
        """Initialize AudioCapture.

        Args:
            sample_rate: Audio sample rate in Hz (must be 16000 for Whisper/VAD).
            channels: Number of audio channels (1 = mono).
            dtype: NumPy dtype string for audio data.
            device_index: sounddevice input device index. None = system default.
            chunk_duration: Duration of each audio chunk in seconds.
            buffer_size: Maximum number of chunks in the circular buffer.
            on_chunk: Optional callback invoked with each new chunk (numpy array).
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.dtype = dtype
        self.device_index = device_index
        self.chunk_duration = chunk_duration
        self.on_chunk = on_chunk

        self.chunk_samples = int(sample_rate * chunk_duration)
        self.buffer = CircularBuffer(capacity=buffer_size)
        self._stream = None
        self._running = threading.Event()
        self._accumulator = np.array([], dtype=dtype)

    def _callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: object,
        status: object,
    ) -> None:
        """sounddevice stream callback — called in a separate thread."""
        if status:
            logger.warning("Audio capture status: %s", status)

        audio_chunk = indata[:, 0].copy() if self.channels == 1 else indata.copy()
        self._accumulator = np.concatenate([self._accumulator, audio_chunk])

        while len(self._accumulator) >= self.chunk_samples:
            chunk = self._accumulator[: self.chunk_samples].copy()
            self._accumulator = self._accumulator[self.chunk_samples :]
            self.buffer.put(chunk)
            if self.on_chunk is not None:
                self.on_chunk(chunk)

    def start(self) -> None:
        """Start audio capture stream."""
        import sounddevice as sd

        if self._running.is_set():
            logger.warning("AudioCapture is already running.")
            return

        logger.info(
            "Starting audio capture: device=%s, rate=%dHz, chunk=%.2fs",
            self.device_index,
            self.sample_rate,
            self.chunk_duration,
        )
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=self.dtype,
            device=self.device_index,
            blocksize=int(self.sample_rate * 0.1),  # 100ms blocks from sounddevice
            callback=self._callback,
        )
        self._stream.start()
        self._running.set()
        logger.info("Audio capture started.")

    def stop(self) -> None:
        """Stop audio capture stream."""
        if not self._running.is_set():
            return
        self._running.clear()
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        logger.info("Audio capture stopped.")

    def read_chunk(self, timeout: float = 1.0) -> Optional[np.ndarray]:
        """Read the next audio chunk from the buffer.

        Args:
            timeout: Seconds to wait for a chunk before returning None.

        Returns:
            NumPy array of shape (chunk_samples,) or None on timeout.
        """
        return self.buffer.get(timeout=timeout)

    @property
    def is_running(self) -> bool:
        """Return True if capture is active."""
        return self._running.is_set()

    @staticmethod
    def list_devices() -> list:
        """Return list of available audio input devices."""
        import sounddevice as sd

        devices = sd.query_devices()
        return [
            {"index": i, "name": d["name"], "channels": d["max_input_channels"]}
            for i, d in enumerate(devices)
            if d["max_input_channels"] > 0
        ]

    def __enter__(self) -> "AudioCapture":
        self.start()
        return self

    def __exit__(self, *args: object) -> None:
        self.stop()
