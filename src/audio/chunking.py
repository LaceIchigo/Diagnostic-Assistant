"""Audio chunking with configurable window size and overlap."""

from typing import Generator, List

import numpy as np


class AudioChunker:
    """Splits a continuous audio stream into overlapping chunks.

    Each chunk has a fixed duration and overlaps with the previous chunk
    by a configurable amount, improving context continuity for ASR and VAD.
    """

    def __init__(
        self,
        chunk_duration: float = 1.5,
        overlap_duration: float = 0.5,
        sample_rate: int = 16000,
    ) -> None:
        """Initialize AudioChunker.

        Args:
            chunk_duration: Duration of each chunk in seconds.
            overlap_duration: Duration of overlap between consecutive chunks.
            sample_rate: Audio sample rate in Hz.
        """
        if overlap_duration >= chunk_duration:
            raise ValueError(
                f"overlap_duration ({overlap_duration}s) must be less than "
                f"chunk_duration ({chunk_duration}s)"
            )

        self.chunk_duration = chunk_duration
        self.overlap_duration = overlap_duration
        self.sample_rate = sample_rate

        self.chunk_samples = int(chunk_duration * sample_rate)
        self.overlap_samples = int(overlap_duration * sample_rate)
        self.hop_samples = self.chunk_samples - self.overlap_samples

        self._buffer = np.array([], dtype=np.float32)
        self._position = 0  # Start time in samples of the current buffer head

    def feed(self, audio: np.ndarray) -> List[np.ndarray]:
        """Feed new audio samples and return ready chunks.

        Args:
            audio: 1-D numpy array of audio samples (float32).

        Returns:
            List of chunks, each of shape (chunk_samples,).
        """
        self._buffer = np.concatenate([self._buffer, audio.astype(np.float32)])
        chunks = []

        while len(self._buffer) >= self.chunk_samples:
            chunk = self._buffer[: self.chunk_samples].copy()
            chunks.append(chunk)
            self._buffer = self._buffer[self.hop_samples :]
            self._position += self.hop_samples

        return chunks

    def chunk_stream(
        self, audio_stream: Generator[np.ndarray, None, None]
    ) -> Generator[np.ndarray, None, None]:
        """Yield overlapping chunks from a generator of audio arrays.

        Args:
            audio_stream: Generator that yields 1-D numpy arrays.

        Yields:
            Overlapping audio chunks of shape (chunk_samples,).
        """
        for audio in audio_stream:
            yield from self.feed(audio)

    @staticmethod
    def chunk_array(
        audio: np.ndarray,
        chunk_samples: int,
        hop_samples: int,
    ) -> List[np.ndarray]:
        """Split a complete audio array into overlapping chunks (static helper).

        Args:
            audio: 1-D numpy array of audio samples.
            chunk_samples: Number of samples per chunk.
            hop_samples: Number of samples to advance between chunks.

        Returns:
            List of chunks.
        """
        chunks = []
        start = 0
        while start + chunk_samples <= len(audio):
            chunks.append(audio[start : start + chunk_samples].copy())
            start += hop_samples
        return chunks

    def reset(self) -> None:
        """Reset internal buffer (e.g., at start of new recording session)."""
        self._buffer = np.array([], dtype=np.float32)
        self._position = 0

    @property
    def chunk_start_time(self) -> float:
        """Return the start time (seconds) of audio currently in the buffer."""
        return self._position / self.sample_rate
