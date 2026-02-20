"""Whisper ASR wrapper with word-level timestamps and Romanian language support."""

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class WordTimestamp:
    """Represents a single transcribed word with timing information."""

    word: str
    start: float   # Start time in seconds
    end: float     # End time in seconds
    probability: float = 1.0  # ASR confidence


@dataclass
class TranscribedSegment:
    """Represents a transcribed segment (sentence/utterance) with word timestamps."""

    text: str
    start: float
    end: float
    words: List[WordTimestamp] = field(default_factory=list)
    language: str = "ro"
    no_speech_prob: float = 0.0

    @property
    def duration(self) -> float:
        """Segment duration in seconds."""
        return self.end - self.start


class WhisperASR:
    """Whisper-based ASR with support for word-level timestamps.

    Uses faster-whisper (CTranslate2 backend) for improved performance
    on AMD GPU via ROCm. Falls back to openai-whisper if faster-whisper
    is unavailable.
    """

    def __init__(
        self,
        model_size: str = "medium",
        language: str = "ro",
        device: str = "cuda",
        compute_type: str = "float16",
        beam_size: int = 5,
        word_timestamps: bool = True,
        download_root: Optional[str] = None,
        initial_prompt: Optional[str] = None,
    ) -> None:
        """Initialize WhisperASR.

        Args:
            model_size: Whisper model size (tiny/base/small/medium/large-v2/large-v3).
            language: Language code for transcription (e.g., "ro" for Romanian).
            device: PyTorch device. Use "cuda" for ROCm AMD GPU.
            compute_type: Quantization type ("float16", "int8", "float32").
            beam_size: Beam search width (higher = more accurate, slower).
            word_timestamps: Whether to generate word-level timestamps.
            download_root: Model cache directory (None = default).
            initial_prompt: Optional prompt to guide transcription style.
        """
        self.model_size = model_size
        self.language = language
        self.device = device
        self.compute_type = compute_type
        self.beam_size = beam_size
        self.word_timestamps = word_timestamps
        self.download_root = download_root
        self.initial_prompt = initial_prompt

        self._model = None
        self._backend: Optional[str] = None

    def load(self) -> None:
        """Load the Whisper model (tries faster-whisper, then openai-whisper)."""
        try:
            self._load_faster_whisper()
        except ImportError:
            logger.warning(
                "faster-whisper not available, falling back to openai-whisper"
            )
            self._load_openai_whisper()

    def _load_faster_whisper(self) -> None:
        """Load model using faster-whisper backend."""
        from faster_whisper import WhisperModel  # type: ignore

        logger.info(
            "Loading faster-whisper model: %s (device=%s, compute_type=%s)",
            self.model_size,
            self.device,
            self.compute_type,
        )
        self._model = WhisperModel(
            self.model_size,
            device=self.device,
            compute_type=self.compute_type,
            download_root=self.download_root,
        )
        self._backend = "faster-whisper"
        logger.info("faster-whisper model loaded.")

    def _load_openai_whisper(self) -> None:
        """Load model using openai-whisper backend."""
        import whisper  # type: ignore

        logger.info(
            "Loading openai-whisper model: %s (device=%s)",
            self.model_size,
            self.device,
        )
        self._model = whisper.load_model(
            self.model_size,
            device=self.device,
            download_root=self.download_root,
        )
        self._backend = "openai-whisper"
        logger.info("openai-whisper model loaded.")

    @property
    def model(self):
        """Return the loaded model, loading if necessary."""
        if self._model is None:
            self.load()
        return self._model

    def transcribe(
        self, audio: np.ndarray, time_offset: float = 0.0
    ) -> List[TranscribedSegment]:
        """Transcribe an audio array and return segments with timestamps.

        Args:
            audio: 1-D numpy float32 array at 16kHz.
            time_offset: Time offset (seconds) to add to all timestamps.
                         Useful when transcribing chunks from a longer stream.

        Returns:
            List of TranscribedSegment objects with text and timestamps.
        """
        if self._backend == "faster-whisper" or self._backend is None:
            return self._transcribe_faster(audio, time_offset)
        return self._transcribe_openai(audio, time_offset)

    def _transcribe_faster(
        self, audio: np.ndarray, time_offset: float
    ) -> List[TranscribedSegment]:
        """Transcribe using faster-whisper backend."""
        segments_iter, info = self.model.transcribe(
            audio,
            language=self.language,
            beam_size=self.beam_size,
            word_timestamps=self.word_timestamps,
            initial_prompt=self.initial_prompt,
        )

        result = []
        for seg in segments_iter:
            words = []
            if self.word_timestamps and seg.words:
                words = [
                    WordTimestamp(
                        word=w.word,
                        start=w.start + time_offset,
                        end=w.end + time_offset,
                        probability=w.probability,
                    )
                    for w in seg.words
                ]
            result.append(
                TranscribedSegment(
                    text=seg.text.strip(),
                    start=seg.start + time_offset,
                    end=seg.end + time_offset,
                    words=words,
                    language=info.language,
                    no_speech_prob=seg.no_speech_prob,
                )
            )
        return result

    def _transcribe_openai(
        self, audio: np.ndarray, time_offset: float
    ) -> List[TranscribedSegment]:
        """Transcribe using openai-whisper backend."""
        result = self.model.transcribe(
            audio,
            language=self.language,
            beam_size=self.beam_size,
            word_timestamps=self.word_timestamps,
            initial_prompt=self.initial_prompt,
            verbose=False,
        )

        segments = []
        for seg in result.get("segments", []):
            words = []
            if self.word_timestamps:
                for w in seg.get("words", []):
                    words.append(
                        WordTimestamp(
                            word=w["word"],
                            start=w["start"] + time_offset,
                            end=w["end"] + time_offset,
                            probability=w.get("probability", 1.0),
                        )
                    )
            segments.append(
                TranscribedSegment(
                    text=seg["text"].strip(),
                    start=seg["start"] + time_offset,
                    end=seg["end"] + time_offset,
                    words=words,
                    language=result.get("language", self.language),
                    no_speech_prob=seg.get("no_speech_prob", 0.0),
                )
            )
        return segments
