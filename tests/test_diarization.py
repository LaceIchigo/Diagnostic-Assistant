"""Tests for diarization module using mocked pyannote pipeline."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from unittest.mock import MagicMock, patch, mock_open

import numpy as np
import pytest

from diarization.pyannote_diar import PyannoteDiarizer, SpeakerTurn


SAMPLE_RATE = 16000


def make_audio(duration: float = 5.0) -> np.ndarray:
    return (0.1 * np.random.randn(int(duration * SAMPLE_RATE))).astype(np.float32)


def make_mock_annotation(turns):
    """Create a mock pyannote Annotation from (start, end, speaker) tuples."""
    mock_annotation = MagicMock()

    def itertracks(yield_label=False):
        for start, end, speaker in turns:
            segment = MagicMock()
            segment.start = start
            segment.end = end
            yield segment, None, speaker

    mock_annotation.itertracks = itertracks
    return mock_annotation


class TestSpeakerTurn:
    def test_duration(self):
        turn = SpeakerTurn(speaker="SPEAKER_00", start=1.0, end=4.5)
        assert turn.duration == pytest.approx(3.5)


class TestPyannoteDiarizer:
    def _make_diarizer_with_mock(self, turns):
        """Create PyannoteDiarizer with mocked pipeline."""
        diarizer = PyannoteDiarizer(
            use_auth_token="fake_token",
            min_speakers=2,
            max_speakers=2,
            window_size=20.0,
            step_size=10.0,
        )
        mock_pipeline = MagicMock()
        mock_pipeline.return_value = make_mock_annotation(turns)
        diarizer._pipeline = mock_pipeline
        return diarizer

    @patch("diarization.pyannote_diar.scipy.io.wavfile.write")
    @patch("diarization.pyannote_diar.os.unlink")
    def test_diarize_returns_speaker_turns(self, mock_unlink, mock_write):
        turns = [(0.0, 2.0, "SPEAKER_00"), (2.5, 5.0, "SPEAKER_01")]
        diarizer = self._make_diarizer_with_mock(turns)

        audio = make_audio(duration=5.0)
        result = diarizer.diarize(audio, SAMPLE_RATE)

        assert len(result) == 2
        assert result[0].speaker == "SPEAKER_00"
        assert result[0].start == pytest.approx(0.0)
        assert result[0].end == pytest.approx(2.0)
        assert result[1].speaker == "SPEAKER_01"

    @patch("diarization.pyannote_diar.scipy.io.wavfile.write")
    @patch("diarization.pyannote_diar.os.unlink")
    def test_diarize_sorted_by_start(self, mock_unlink, mock_write):
        turns = [(3.0, 5.0, "SPEAKER_01"), (0.0, 2.5, "SPEAKER_00")]
        diarizer = self._make_diarizer_with_mock(turns)

        result = diarizer.diarize(make_audio(5.0), SAMPLE_RATE)
        starts = [t.start for t in result]
        assert starts == sorted(starts)

    def test_merge_overlapping_turns_same_speaker(self):
        turns = [
            SpeakerTurn("SPEAKER_00", 0.0, 2.0),
            SpeakerTurn("SPEAKER_00", 1.5, 3.5),
        ]
        merged = PyannoteDiarizer._merge_overlapping_turns(turns)
        assert len(merged) == 1
        assert merged[0].start == pytest.approx(0.0)
        assert merged[0].end == pytest.approx(3.5)

    def test_merge_non_overlapping_turns(self):
        turns = [
            SpeakerTurn("SPEAKER_00", 0.0, 1.0),
            SpeakerTurn("SPEAKER_01", 1.5, 3.0),
        ]
        merged = PyannoteDiarizer._merge_overlapping_turns(turns)
        assert len(merged) == 2

    @patch("diarization.pyannote_diar.scipy.io.wavfile.write")
    @patch("diarization.pyannote_diar.os.unlink")
    def test_diarize_sliding_short_audio(self, mock_unlink, mock_write):
        """For audio shorter than window_size, sliding = regular diarize."""
        turns = [(0.0, 1.0, "SPEAKER_00"), (1.5, 3.0, "SPEAKER_01")]
        diarizer = self._make_diarizer_with_mock(turns)

        # Audio shorter than window_size=20s
        audio = make_audio(duration=5.0)
        result = diarizer.diarize_sliding(audio, SAMPLE_RATE)
        assert len(result) >= 1
