"""Tests for Silero VAD module using synthetic audio."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import torch

from vad.silero_vad import SileroVAD, SpeechSegment


SAMPLE_RATE = 16000


def make_silence(duration: float = 1.0) -> np.ndarray:
    """Generate silence."""
    return np.zeros(int(duration * SAMPLE_RATE), dtype=np.float32)


def make_tone(frequency: float = 440.0, duration: float = 1.0) -> np.ndarray:
    """Generate a sine wave tone."""
    t = np.linspace(0, duration, int(duration * SAMPLE_RATE), endpoint=False)
    return (0.5 * np.sin(2 * np.pi * frequency * t)).astype(np.float32)


class TestSpeechSegment:
    def test_duration(self):
        seg = SpeechSegment(start=1.0, end=3.5)
        assert seg.duration == pytest.approx(2.5)

    def test_repr(self):
        seg = SpeechSegment(start=0.5, end=1.5)
        assert seg.start == 0.5
        assert seg.end == 1.5


class TestSileroVAD:
    """Tests for SileroVAD using a mocked torch.hub model."""

    def _make_mock_vad(self, speech_prob: float = 0.8):
        """Create a SileroVAD instance with mocked model."""
        vad = SileroVAD(threshold=0.5, device="cpu")

        # Create a return value with .item() method that returns speech_prob
        mock_return = MagicMock()
        mock_return.item.return_value = speech_prob

        mock_model = MagicMock()
        mock_model.return_value = mock_return
        vad._model = mock_model

        mock_get_speech_ts = MagicMock(return_value=[{"start": 0.1, "end": 0.9}])
        vad._utils = (mock_get_speech_ts,)

        return vad

    def test_get_speech_probability_above_threshold(self):
        vad = self._make_mock_vad(speech_prob=0.9)
        audio = make_tone(duration=0.5)
        prob = vad.get_speech_probability(audio)
        assert 0.0 <= prob <= 1.0
        assert prob == pytest.approx(0.9)

    def test_get_speech_probability_below_threshold(self):
        vad = self._make_mock_vad(speech_prob=0.1)
        audio = make_silence(duration=0.5)
        prob = vad.get_speech_probability(audio)
        assert prob == pytest.approx(0.1)

    def test_is_speech_true(self):
        vad = self._make_mock_vad(speech_prob=0.9)
        audio = make_tone(duration=0.5)
        assert vad.is_speech(audio) is True

    def test_is_speech_false(self):
        vad = self._make_mock_vad(speech_prob=0.1)
        audio = make_silence(duration=0.5)
        assert vad.is_speech(audio) is False

    def test_get_speech_segments(self):
        vad = self._make_mock_vad()
        audio = np.concatenate([make_tone(duration=1.0), make_silence(duration=0.5)])
        segments = vad.get_speech_segments(audio, SAMPLE_RATE)

        assert len(segments) == 1
        assert isinstance(segments[0], SpeechSegment)
        assert segments[0].start == pytest.approx(0.1)
        assert segments[0].end == pytest.approx(0.9)

    def test_wrong_sample_rate_raises(self):
        vad = self._make_mock_vad()
        audio = make_tone(duration=1.0)
        with pytest.raises(ValueError, match="16kHz"):
            vad.get_speech_segments(audio, sample_rate=8000)

    def test_device_defaults_to_cpu_when_no_cuda(self):
        with patch("vad.silero_vad.torch.cuda.is_available", return_value=False):
            vad = SileroVAD()
            assert str(vad.device) == "cpu"

    def test_reset_states(self):
        vad = self._make_mock_vad()
        # Should not raise even with mock
        vad.reset_states()
        vad._model.reset_states.assert_called_once()
