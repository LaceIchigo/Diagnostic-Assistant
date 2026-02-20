"""End-to-end pipeline integration test."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from asr.whisper_asr import TranscribedSegment, WordTimestamp
from diarization.pyannote_diar import SpeakerTurn
from pipeline.orchestrator import PipelineConfig, PipelineOrchestrator, PipelineOutput
from postprocessing.role_labeling import MedicalRole


SAMPLE_RATE = 16000


def make_audio(duration: float = 5.0) -> np.ndarray:
    t = np.linspace(0, duration, int(duration * SAMPLE_RATE), endpoint=False)
    return (0.3 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)


def make_mock_vad_with_speech():
    from vad.silero_vad import SpeechSegment
    mock_vad = MagicMock()
    mock_vad.get_speech_segments.return_value = [SpeechSegment(0.0, 5.0)]
    return mock_vad


def make_mock_asr():
    mock_asr = MagicMock()
    mock_asr.transcribe.return_value = [
        TranscribedSegment(
            text="Bună ziua, ce probleme aveți?",
            start=0.0,
            end=2.5,
            words=[
                WordTimestamp("Bună", 0.0, 0.3, 0.99),
                WordTimestamp("ziua", 0.4, 0.7, 0.98),
            ],
        ),
        TranscribedSegment(
            text="Am dureri de cap.",
            start=3.0,
            end=5.0,
            words=[
                WordTimestamp("Am", 3.0, 3.2, 0.97),
            ],
        ),
    ]
    return mock_asr


def make_mock_diarizer():
    mock_diar = MagicMock()
    mock_diar.diarize_sliding.return_value = [
        SpeakerTurn("SPEAKER_00", 0.0, 2.7),
        SpeakerTurn("SPEAKER_01", 2.9, 5.5),
    ]
    return mock_diar


class TestPipelineE2E:
    def _make_orchestrator_with_mocks(self):
        """Create a fully mocked PipelineOrchestrator."""
        config = PipelineConfig(
            model_size="tiny",
            language="ro",
            device="cpu",
            output_dir="/tmp/test_output",
        )
        orch = PipelineOrchestrator(config=config)
        orch.vad = make_mock_vad_with_speech()
        orch.asr = make_mock_asr()
        orch.diarizer = make_mock_diarizer()
        return orch

    def test_process_audio_returns_output(self):
        orch = self._make_orchestrator_with_mocks()
        audio = make_audio(duration=5.0)
        output = orch.process_audio(audio)

        assert isinstance(output, PipelineOutput)
        assert len(output.segments) == 2

    def test_process_audio_assigns_speaker(self):
        orch = self._make_orchestrator_with_mocks()
        audio = make_audio(duration=5.0)
        output = orch.process_audio(audio)

        speakers = {seg.speaker for seg in output.segments}
        assert "SPEAKER_00" in speakers
        assert "SPEAKER_01" in speakers

    def test_process_audio_assigns_roles(self):
        orch = self._make_orchestrator_with_mocks()
        audio = make_audio(duration=5.0)
        output = orch.process_audio(audio)

        roles = {getattr(seg, "role", None) for seg in output.segments}
        # At least one role should be assigned
        assert any(r in (MedicalRole.DOCTOR, MedicalRole.PATIENT) for r in roles)

    def test_process_audio_no_speech(self):
        orch = self._make_orchestrator_with_mocks()
        orch.vad.get_speech_segments.return_value = []  # No speech

        audio = make_audio(duration=5.0)
        output = orch.process_audio(audio)

        assert len(output.segments) == 0

    def test_save_output(self, tmp_path):
        orch = self._make_orchestrator_with_mocks()
        orch.config.output_dir = str(tmp_path)

        audio = make_audio(duration=5.0)
        output = orch.process_audio(audio)
        saved_path = orch.save_output(output, "test_transcript.json")

        assert os.path.exists(saved_path)
        import json
        with open(saved_path) as f:
            data = json.load(f)
        assert "segments" in data

    def test_output_to_dict(self):
        orch = self._make_orchestrator_with_mocks()
        audio = make_audio(duration=5.0)
        output = orch.process_audio(audio)
        data = output.to_dict()

        assert "segments" in data
        assert "timestamp" in data
        for seg_data in data["segments"]:
            assert "speaker" in seg_data
            assert "text" in seg_data
            assert "start" in seg_data
            assert "end" in seg_data

    def test_from_yaml_creates_orchestrator(self, tmp_path):
        config_yaml = tmp_path / "test_config.yaml"
        config_yaml.write_text("""
audio:
  sample_rate: 16000
  channels: 1
  chunk_duration: 1.5
  overlap: 0.5
pipeline:
  language: ro
  device: cpu
  model_size: tiny
""")
        orch = PipelineOrchestrator.from_yaml(str(config_yaml))
        assert orch.config.sample_rate == 16000
        assert orch.config.language == "ro"
