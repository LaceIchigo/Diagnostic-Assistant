"""Pyannote.audio diarization wrapper with sliding window support."""

import os
import tempfile
from dataclasses import dataclass
from typing import List, Optional

import numpy as np
import scipy.io.wavfile

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SpeakerTurn:
    """Represents a continuous segment attributed to a single speaker."""

    speaker: str   # Speaker identifier, e.g., "SPEAKER_00"
    start: float   # Start time in seconds
    end: float     # End time in seconds

    @property
    def duration(self) -> float:
        """Duration in seconds."""
        return self.end - self.start


class PyannoteDiarizer:
    """Speaker diarization using pyannote.audio with sliding window.

    Processes audio in overlapping windows to handle long recordings
    while maintaining speaker identity across windows.
    """

    def __init__(
        self,
        pipeline_name: str = "pyannote/speaker-diarization-3.1",
        use_auth_token: Optional[str] = None,
        min_speakers: int = 2,
        max_speakers: int = 2,
        window_size: float = 20.0,
        step_size: float = 10.0,
        device: Optional[str] = None,
    ) -> None:
        """Initialize PyannoteDiarizer.

        Args:
            pipeline_name: HuggingFace model ID for pyannote pipeline.
            use_auth_token: HuggingFace token (or reads HUGGINGFACE_TOKEN env var).
            min_speakers: Minimum number of speakers to detect.
            max_speakers: Maximum number of speakers to detect.
            window_size: Sliding window size in seconds.
            step_size: Step size between windows in seconds.
            device: PyTorch device string. None = auto-detect.
        """
        self.pipeline_name = pipeline_name
        self.use_auth_token = use_auth_token or os.environ.get("HUGGINGFACE_TOKEN")
        self.min_speakers = min_speakers
        self.max_speakers = max_speakers
        self.window_size = window_size
        self.step_size = step_size

        if device is None:
            import torch
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        self._pipeline = None

    def load(self) -> None:
        """Load the pyannote diarization pipeline."""
        from pyannote.audio import Pipeline  # type: ignore
        import torch

        logger.info(
            "Loading pyannote pipeline: %s (device=%s)", self.pipeline_name, self.device
        )
        self._pipeline = Pipeline.from_pretrained(
            self.pipeline_name,
            use_auth_token=self.use_auth_token,
        )
        self._pipeline = self._pipeline.to(torch.device(self.device))
        logger.info("Pyannote pipeline loaded.")

    @property
    def pipeline(self):
        """Return the loaded pipeline, loading if necessary."""
        if self._pipeline is None:
            self.load()
        return self._pipeline

    def diarize(
        self, audio: np.ndarray, sample_rate: int = 16000
    ) -> List[SpeakerTurn]:
        """Perform speaker diarization on an audio array.

        Args:
            audio: 1-D numpy float32 array at the given sample rate.
            sample_rate: Audio sample rate in Hz.

        Returns:
            List of SpeakerTurn sorted by start time.
        """
        # Write to a temporary WAV file (pyannote expects file path or dict)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            audio_int16 = (audio * 32767).astype(np.int16)
            scipy.io.wavfile.write(tmp_path, sample_rate, audio_int16)

            diarization = self.pipeline(
                tmp_path,
                min_speakers=self.min_speakers,
                max_speakers=self.max_speakers,
            )
        finally:
            os.unlink(tmp_path)

        turns = []
        for segment, _, speaker in diarization.itertracks(yield_label=True):
            turns.append(
                SpeakerTurn(
                    speaker=speaker,
                    start=segment.start,
                    end=segment.end,
                )
            )

        return sorted(turns, key=lambda t: t.start)

    def diarize_sliding(
        self, audio: np.ndarray, sample_rate: int = 16000
    ) -> List[SpeakerTurn]:
        """Diarize a long audio using sliding windows.

        For long recordings (> window_size), processes overlapping windows
        and merges the results.

        Args:
            audio: 1-D numpy float32 array.
            sample_rate: Audio sample rate in Hz.

        Returns:
            List of SpeakerTurn sorted by start time.
        """
        duration = len(audio) / sample_rate

        if duration <= self.window_size:
            return self.diarize(audio, sample_rate)

        window_samples = int(self.window_size * sample_rate)
        step_samples = int(self.step_size * sample_rate)

        all_turns: List[SpeakerTurn] = []
        start_sample = 0

        while start_sample < len(audio):
            end_sample = min(start_sample + window_samples, len(audio))
            window_audio = audio[start_sample:end_sample]
            time_offset = start_sample / sample_rate

            window_turns = self.diarize(window_audio, sample_rate)
            for turn in window_turns:
                all_turns.append(
                    SpeakerTurn(
                        speaker=turn.speaker,
                        start=turn.start + time_offset,
                        end=turn.end + time_offset,
                    )
                )

            start_sample += step_samples

        return self._merge_overlapping_turns(all_turns)

    @staticmethod
    def _merge_overlapping_turns(turns: List[SpeakerTurn]) -> List[SpeakerTurn]:
        """Merge adjacent turns from the same speaker, removing duplicates."""
        if not turns:
            return turns

        turns = sorted(turns, key=lambda t: t.start)
        merged = [turns[0]]

        for turn in turns[1:]:
            last = merged[-1]
            if turn.speaker == last.speaker and turn.start <= last.end:
                merged[-1] = SpeakerTurn(
                    speaker=last.speaker,
                    start=last.start,
                    end=max(last.end, turn.end),
                )
            else:
                merged.append(turn)

        return merged
