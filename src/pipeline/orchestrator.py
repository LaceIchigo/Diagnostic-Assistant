"""Full pipeline orchestrator: audio → VAD → ASR → diarization → alignment → output."""

import json
import os
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import yaml

from asr.whisper_asr import WhisperASR
from audio.capture import AudioCapture
from audio.chunking import AudioChunker
from audio.preprocessing import AudioPreprocessor
from diarization.alignment import AlignedSegment, DiarizationAligner
from diarization.pyannote_diar import PyannoteDiarizer
from postprocessing.punctuation import PunctuationProcessor
from postprocessing.role_labeling import MedicalRole, RoleLabeler
from utils.circular_buffer import CircularBuffer
from utils.logger import get_logger
from vad.silero_vad import SileroVAD

logger = get_logger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for the pipeline orchestrator."""

    sample_rate: int = 16000
    channels: int = 1
    chunk_duration: float = 1.5
    overlap: float = 0.5
    language: str = "ro"
    device: str = "cuda"
    model_size: str = "medium"
    vad_threshold: float = 0.5
    diarization_window: float = 20.0
    diarization_step: float = 10.0
    max_speakers: int = 2
    output_dir: str = "./output"


@dataclass
class PipelineOutput:
    """Structured output from the pipeline for one processing cycle."""

    segments: List[AlignedSegment] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    processing_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        def safe_role(seg) -> str:
            role = getattr(seg, "role", None)
            if role is None:
                return "Necunoscut"
            if isinstance(role, MedicalRole):
                return role.value
            if isinstance(role, str):
                return role
            try:
                return str(role.value)
            except Exception:
                return "Necunoscut"

        return {
            "timestamp": self.timestamp,
            "processing_time": self.processing_time,
            "segments": [
                {
                    "speaker": str(seg.speaker),
                    "role": safe_role(seg),
                    "text": str(seg.text),
                    "start": float(seg.start),
                    "end": float(seg.end),
                }
                for seg in self.segments
            ],
        }


class PipelineOrchestrator:
    """Orchestrates the complete Diagnostic Assistant pipeline.

    Chains: AudioCapture → VAD → ASR → Diarization → Alignment
           → Punctuation → RoleLabeling → structured output.
    """

    def __init__(self, config: Optional[PipelineConfig] = None) -> None:
        """Initialize the pipeline orchestrator.

        Args:
            config: Pipeline configuration. Defaults to PipelineConfig().
        """
        self.config = config or PipelineConfig()

        self.preprocessor = AudioPreprocessor(
            target_sample_rate=self.config.sample_rate
        )
        self.chunker = AudioChunker(
            chunk_duration=self.config.chunk_duration,
            overlap_duration=self.config.overlap,
            sample_rate=self.config.sample_rate,
        )
        self.vad = SileroVAD(
            threshold=self.config.vad_threshold,
            device=self.config.device,
        )
        self.asr = WhisperASR(
            model_size=self.config.model_size,
            language=self.config.language,
            device=self.config.device,
        )
        self.diarizer = PyannoteDiarizer(
            min_speakers=2,
            max_speakers=self.config.max_speakers,
            window_size=self.config.diarization_window,
            step_size=self.config.diarization_step,
            device=self.config.device,
        )
        self.aligner = DiarizationAligner()
        self.punctuation = PunctuationProcessor(device=self.config.device)
        self.role_labeler = RoleLabeler()

        self._audio_buffer: List[np.ndarray] = []

    @classmethod
    def from_yaml(cls, config_path: str) -> "PipelineOrchestrator":
        """Create orchestrator from a YAML configuration file.

        Args:
            config_path: Path to YAML config file.

        Returns:
            Configured PipelineOrchestrator instance.
        """
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        audio_cfg = cfg.get("audio", {})
        pipeline_cfg = cfg.get("pipeline", {})
        config = PipelineConfig(
            sample_rate=audio_cfg.get("sample_rate", 16000),
            channels=audio_cfg.get("channels", 1),
            chunk_duration=audio_cfg.get("chunk_duration", 1.5),
            overlap=audio_cfg.get("overlap", 0.5),
            language=pipeline_cfg.get("language", "ro"),
            device=pipeline_cfg.get("device", "cuda"),
            model_size=pipeline_cfg.get("model_size", "medium"),
        )
        return cls(config=config)

    def process_audio(self, audio: np.ndarray) -> PipelineOutput:
        """Process a single audio array through the full pipeline.

        Args:
            audio: 1-D numpy float32 array at self.config.sample_rate.

        Returns:
            PipelineOutput with aligned, labeled segments.
        """
        start_time = time.time()

        # 1. Preprocess (already at correct sample rate)
        audio = self.preprocessor.process(audio, self.config.sample_rate)

        # 2. VAD — filter speech segments
        speech_segments = self.vad.get_speech_segments(audio, self.config.sample_rate)
        if not speech_segments:
            logger.debug("No speech detected in chunk.")
            return PipelineOutput(processing_time=time.time() - start_time)

        # 3. ASR
        asr_segments = self.asr.transcribe(audio)
        if not asr_segments:
            return PipelineOutput(processing_time=time.time() - start_time)

        # 4. Diarization
        speaker_turns = self.diarizer.diarize_sliding(audio, self.config.sample_rate)

        # 5. Alignment
        aligned = self.aligner.align(asr_segments, speaker_turns)

        # 6. Punctuation
        self.punctuation.process_segments(aligned)

        # 7. Role labeling
        self.role_labeler.label_segments(aligned)

        processing_time = time.time() - start_time
        logger.info(
            "Processed %.1fs of audio in %.2fs (%.1fx real-time)",
            len(audio) / self.config.sample_rate,
            processing_time,
            (len(audio) / self.config.sample_rate) / processing_time
            if processing_time > 0
            else 0,
        )

        return PipelineOutput(segments=aligned, processing_time=processing_time)

    def save_output(self, output: PipelineOutput, filename: str = "transcript.json") -> str:
        """Save pipeline output to a JSON file.

        Args:
            output: PipelineOutput to save.
            filename: Output filename.

        Returns:
            Path to the saved file.
        """
        os.makedirs(self.config.output_dir, exist_ok=True)
        path = os.path.join(self.config.output_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(output.to_dict(), f, ensure_ascii=False, indent=2)
        logger.info("Output saved to %s", path)
        return path


def main() -> None:
    """Entry point for command-line usage."""
    import argparse

    parser = argparse.ArgumentParser(description="Diagnostic Assistant Pipeline")
    parser.add_argument("--config", default="config/default.yaml")
    parser.add_argument("--device-index", type=int, default=0)
    args = parser.parse_args()

    orchestrator = PipelineOrchestrator.from_yaml(args.config)
    capture = AudioCapture(
        sample_rate=orchestrator.config.sample_rate,
        device_index=args.device_index,
        chunk_duration=orchestrator.config.chunk_duration,
    )

    logger.info("Starting pipeline. Press Ctrl+C to stop.")
    with capture:
        while True:
            chunk = capture.read_chunk(timeout=2.0)
            if chunk is not None:
                output = orchestrator.process_audio(chunk)
                for seg in output.segments:
                    role = getattr(seg, "role", MedicalRole.UNKNOWN)
                    print(f"[{seg.start:.1f}s] {role.value}: {seg.text}")


if __name__ == "__main__":
    main()
