"""Silero VAD wrapper — Voice Activity Detection using PyTorch (ROCm compatible)."""

from dataclasses import dataclass
from typing import List, Optional

import numpy as np
import torch

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SpeechSegment:
    """Represents a detected speech segment."""

    start: float  # Start time in seconds
    end: float    # End time in seconds

    @property
    def duration(self) -> float:
        """Duration in seconds."""
        return self.end - self.start


class SileroVAD:
    """Wrapper for Silero VAD model loaded via torch.hub.

    Silero VAD is PyTorch-native and compatible with ROCm (AMD GPU).
    It processes audio chunks and returns speech probability + segments.
    """

    SAMPLE_RATE = 16000  # Silero VAD requires 16kHz audio
    WINDOW_SIZE_SAMPLES = 512  # Supported: 512, 1024, 1536 for 16kHz

    def __init__(
        self,
        threshold: float = 0.5,
        min_speech_duration_ms: int = 250,
        min_silence_duration_ms: int = 100,
        speech_pad_ms: int = 30,
        device: Optional[str] = None,
        force_reload: bool = False,
    ) -> None:
        """Initialize Silero VAD.

        Args:
            threshold: Speech probability threshold [0, 1]. Higher = fewer false positives.
            min_speech_duration_ms: Minimum duration for a speech segment (ms).
            min_silence_duration_ms: Minimum silence gap to split segments (ms).
            speech_pad_ms: Padding added around speech segments (ms).
            device: PyTorch device string. None = auto-detect (cuda > cpu).
            force_reload: Force re-download of the model from torch.hub.
        """
        self.threshold = threshold
        self.min_speech_duration_ms = min_speech_duration_ms
        self.min_silence_duration_ms = min_silence_duration_ms
        self.speech_pad_ms = speech_pad_ms
        self.force_reload = force_reload

        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        self._model: Optional[torch.nn.Module] = None
        self._utils = None

    def load(self) -> None:
        """Load Silero VAD model from torch.hub."""
        logger.info("Loading Silero VAD model (device=%s)...", self.device)
        self._model, self._utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=self.force_reload,
            onnx=False,
        )
        self._model = self._model.to(self.device)
        self._model.eval()
        logger.info("Silero VAD loaded successfully.")

    @property
    def model(self) -> torch.nn.Module:
        """Return the loaded model, loading it if necessary."""
        if self._model is None:
            self.load()
        return self._model

    def get_speech_probability(self, audio_chunk: np.ndarray) -> float:
        """Get speech probability for a single audio chunk.

        Args:
            audio_chunk: 1-D numpy float32 array at 16kHz.

        Returns:
            Speech probability in [0, 1].
        """
        tensor = torch.from_numpy(audio_chunk).to(self.device)
        if tensor.dim() == 1:
            tensor = tensor.unsqueeze(0)

        with torch.no_grad():
            prob = self.model(tensor, self.SAMPLE_RATE).item()

        return float(prob)

    def is_speech(self, audio_chunk: np.ndarray) -> bool:
        """Return True if the chunk contains speech above threshold.

        Args:
            audio_chunk: 1-D numpy float32 array at 16kHz.

        Returns:
            True if speech detected.
        """
        return self.get_speech_probability(audio_chunk) >= self.threshold

    def get_speech_segments(
        self, audio: np.ndarray, sample_rate: int = SAMPLE_RATE
    ) -> List[SpeechSegment]:
        """Detect all speech segments in a longer audio array.

        Args:
            audio: 1-D numpy float32 array.
            sample_rate: Audio sample rate (must be 16000).

        Returns:
            List of SpeechSegment with start/end times in seconds.
        """
        if sample_rate != self.SAMPLE_RATE:
            raise ValueError(
                f"Silero VAD requires 16kHz audio, got {sample_rate}Hz. "
                "Resample before calling get_speech_segments()."
            )

        if self._utils is None:
            self.load()

        get_speech_ts = self._utils[0]  # get_speech_timestamps utility
        tensor = torch.from_numpy(audio).to(self.device)

        speech_timestamps = get_speech_ts(
            tensor,
            self.model,
            threshold=self.threshold,
            sampling_rate=sample_rate,
            min_speech_duration_ms=self.min_speech_duration_ms,
            min_silence_duration_ms=self.min_silence_duration_ms,
            speech_pad_ms=self.speech_pad_ms,
            return_seconds=True,
        )

        return [
            SpeechSegment(start=seg["start"], end=seg["end"])
            for seg in speech_timestamps
        ]

    def reset_states(self) -> None:
        """Reset VAD model internal states (call between audio streams)."""
        if self._model is not None:
            self._model.reset_states()
