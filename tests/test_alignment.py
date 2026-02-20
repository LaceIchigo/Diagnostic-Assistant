"""Tests for diarization-ASR alignment module."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

from asr.whisper_asr import TranscribedSegment, WordTimestamp
from diarization.alignment import AlignedSegment, DiarizationAligner
from diarization.pyannote_diar import SpeakerTurn


def make_asr_segment(text, start, end, words=None):
    return TranscribedSegment(
        text=text, start=start, end=end, words=words or [], language="ro"
    )


def make_speaker_turn(speaker, start, end):
    return SpeakerTurn(speaker=speaker, start=start, end=end)


class TestAlignedSegment:
    def test_duration(self):
        seg = AlignedSegment(speaker="SPEAKER_00", text="test", start=1.0, end=3.0)
        assert seg.duration == pytest.approx(2.0)


class TestDiarizationAligner:
    def setup_method(self):
        self.aligner = DiarizationAligner()

    def test_align_single_segment_single_speaker(self):
        asr = [make_asr_segment("Bună ziua", 0.0, 2.0)]
        turns = [make_speaker_turn("SPEAKER_00", 0.0, 5.0)]
        result = self.aligner.align(asr, turns)

        assert len(result) == 1
        assert result[0].speaker == "SPEAKER_00"
        assert result[0].text == "Bună ziua"

    def test_align_multiple_segments(self):
        asr = [
            make_asr_segment("Bună ziua", 0.0, 2.0),
            make_asr_segment("Am dureri de cap", 3.0, 5.0),
        ]
        turns = [
            make_speaker_turn("SPEAKER_00", 0.0, 2.5),
            make_speaker_turn("SPEAKER_01", 2.8, 6.0),
        ]
        result = self.aligner.align(asr, turns)

        assert len(result) == 2
        assert result[0].speaker == "SPEAKER_00"
        assert result[1].speaker == "SPEAKER_01"

    def test_align_unknown_speaker_when_no_overlap(self):
        asr = [make_asr_segment("Test", 10.0, 12.0)]
        turns = [make_speaker_turn("SPEAKER_00", 0.0, 5.0)]
        result = self.aligner.align(asr, turns)

        assert len(result) == 1
        assert result[0].speaker == "SPEAKER_UNKNOWN"

    def test_align_sorted_by_start(self):
        asr = [
            make_asr_segment("B", 3.0, 5.0),
            make_asr_segment("A", 0.0, 2.0),
        ]
        turns = [make_speaker_turn("SPEAKER_00", 0.0, 6.0)]
        result = self.aligner.align(asr, turns)

        starts = [s.start for s in result]
        assert starts == sorted(starts)

    def test_align_word_level(self):
        words_doc = [
            WordTimestamp("Bună", 0.0, 0.5, 0.99),
            WordTimestamp("ziua", 0.5, 1.0, 0.98),
        ]
        words_pat = [
            WordTimestamp("Am", 1.5, 1.8, 0.97),
            WordTimestamp("dureri", 1.8, 2.2, 0.96),
        ]
        asr = [
            make_asr_segment("Bună ziua", 0.0, 1.0, words=words_doc),
            make_asr_segment("Am dureri", 1.5, 2.5, words=words_pat),
        ]
        turns = [
            make_speaker_turn("SPEAKER_00", 0.0, 1.2),
            make_speaker_turn("SPEAKER_01", 1.4, 3.0),
        ]
        result = self.aligner.align_word_level(asr, turns)

        assert len(result) >= 1
        # Doctor words should be SPEAKER_00
        doc_segs = [s for s in result if s.speaker == "SPEAKER_00"]
        pat_segs = [s for s in result if s.speaker == "SPEAKER_01"]
        assert len(doc_segs) > 0
        assert len(pat_segs) > 0

    def test_align_empty_input(self):
        result = self.aligner.align([], [])
        assert result == []

    def test_align_best_speaker_is_max_overlap(self):
        asr = [make_asr_segment("Test", 1.0, 3.0)]
        turns = [
            make_speaker_turn("SPEAKER_00", 0.0, 1.5),  # overlap = 0.5s
            make_speaker_turn("SPEAKER_01", 1.0, 4.0),  # overlap = 2.0s (best)
        ]
        result = self.aligner.align(asr, turns)
        assert result[0].speaker == "SPEAKER_01"
