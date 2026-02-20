"""Tests for Whisper ASR module."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from asr.whisper_asr import TranscribedSegment, WhisperASR, WordTimestamp


SAMPLE_RATE = 16000


def make_audio(duration: float = 2.0) -> np.ndarray:
    """Generate synthetic audio (sine wave)."""
    t = np.linspace(0, duration, int(duration * SAMPLE_RATE), endpoint=False)
    return (0.3 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)


class TestWordTimestamp:
    def test_fields(self):
        w = WordTimestamp(word="bună", start=0.1, end=0.4, probability=0.95)
        assert w.word == "bună"
        assert w.start == pytest.approx(0.1)
        assert w.end == pytest.approx(0.4)
        assert w.probability == pytest.approx(0.95)


class TestTranscribedSegment:
    def test_duration(self):
        seg = TranscribedSegment(text="test", start=1.0, end=3.5, words=[])
        assert seg.duration == pytest.approx(2.5)

    def test_empty_words(self):
        seg = TranscribedSegment(text="test", start=0.0, end=1.0)
        assert seg.words == []


class TestWhisperASR:
    """Tests for WhisperASR using mocked model backends."""

    def _make_faster_whisper_asr(self):
        """Create WhisperASR with mocked faster-whisper model."""
        asr = WhisperASR(model_size="tiny", language="ro", device="cpu")

        # Mock faster-whisper model
        mock_segment = MagicMock()
        mock_segment.text = "Bună ziua"
        mock_segment.start = 0.0
        mock_segment.end = 1.5
        mock_segment.no_speech_prob = 0.05
        mock_word = MagicMock()
        mock_word.word = "Bună"
        mock_word.start = 0.0
        mock_word.end = 0.5
        mock_word.probability = 0.98
        mock_segment.words = [mock_word]

        mock_info = MagicMock()
        mock_info.language = "ro"

        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([mock_segment], mock_info)
        asr._model = mock_model
        asr._backend = "faster-whisper"
        return asr

    def test_transcribe_returns_segments(self):
        asr = self._make_faster_whisper_asr()
        audio = make_audio(duration=2.0)
        segments = asr.transcribe(audio)

        assert len(segments) == 1
        assert isinstance(segments[0], TranscribedSegment)
        assert segments[0].text == "Bună ziua"
        assert segments[0].start == pytest.approx(0.0)
        assert segments[0].end == pytest.approx(1.5)

    def test_transcribe_with_time_offset(self):
        asr = self._make_faster_whisper_asr()
        audio = make_audio(duration=2.0)
        segments = asr.transcribe(audio, time_offset=10.0)

        assert segments[0].start == pytest.approx(10.0)
        assert segments[0].end == pytest.approx(11.5)

    def test_word_timestamps_present(self):
        asr = self._make_faster_whisper_asr()
        audio = make_audio(duration=2.0)
        segments = asr.transcribe(audio)

        assert len(segments[0].words) == 1
        assert segments[0].words[0].word == "Bună"

    def test_model_property_triggers_load(self):
        asr = WhisperASR(model_size="tiny", language="ro", device="cpu")
        with patch.object(asr, "load") as mock_load:
            mock_load.side_effect = lambda: setattr(asr, "_model", MagicMock())
            # Access model property
            try:
                _ = asr.model
            except Exception:
                pass
            # load() should have been called
            mock_load.assert_called_once()

    def test_openai_whisper_fallback(self):
        """Test that openai-whisper backend is parsed correctly."""
        asr = WhisperASR(model_size="tiny", language="ro", device="cpu")
        asr._backend = "openai-whisper"

        mock_model = MagicMock()
        mock_model.transcribe.return_value = {
            "language": "ro",
            "segments": [
                {
                    "text": "Test",
                    "start": 0.0,
                    "end": 1.0,
                    "no_speech_prob": 0.0,
                    "words": [{"word": "Test", "start": 0.0, "end": 0.5, "probability": 0.9}],
                }
            ],
        }
        asr._model = mock_model

        segments = asr.transcribe(make_audio())
        assert len(segments) == 1
        assert segments[0].text == "Test"
