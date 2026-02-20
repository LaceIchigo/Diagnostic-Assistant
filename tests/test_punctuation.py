"""Tests for punctuation processing module."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from unittest.mock import MagicMock, patch

import pytest

from postprocessing.punctuation import PunctuationProcessor
from diarization.alignment import AlignedSegment


class TestPunctuationProcessor:
    def test_fallback_capitalizes_first_letter(self):
        proc = PunctuationProcessor()
        result = proc._fallback_punctuation("bună ziua")
        assert result[0].isupper()

    def test_fallback_adds_period_if_missing(self):
        proc = PunctuationProcessor()
        result = proc._fallback_punctuation("bună ziua")
        assert result.endswith(".")

    def test_fallback_keeps_existing_punctuation(self):
        proc = PunctuationProcessor()
        result = proc._fallback_punctuation("Bună ziua!")
        assert result.endswith("!")
        assert not result.endswith("!.")

    def test_fallback_empty_string(self):
        proc = PunctuationProcessor()
        assert proc._fallback_punctuation("") == ""
        assert proc._fallback_punctuation("   ") == ""

    def test_add_punctuation_uses_model_when_loaded(self):
        proc = PunctuationProcessor()
        mock_model = MagicMock()
        mock_model.restore_punctuation.return_value = "Bună ziua, cum vă simțiți?"
        proc._model = mock_model

        result = proc.add_punctuation("buna ziua cum va simtiti")
        assert result == "Bună ziua, cum vă simțiți?"

    def test_add_punctuation_uses_fallback_when_model_none(self):
        proc = PunctuationProcessor()
        proc._model = None  # Force no model

        with patch.object(proc, "load"):  # Prevent actual loading
            # Bypass load by directly returning None from model property
            with patch.object(type(proc), "model", property(lambda self: None)):
                result = proc.add_punctuation("test text")
                assert result[0].isupper()

    def test_add_punctuation_falls_back_on_model_error(self):
        proc = PunctuationProcessor()
        mock_model = MagicMock()
        mock_model.restore_punctuation.side_effect = RuntimeError("GPU error")
        proc._model = mock_model

        result = proc.add_punctuation("test text")
        # Should use fallback
        assert len(result) > 0

    def test_process_segments_updates_text(self):
        proc = PunctuationProcessor()
        proc._model = None  # Use fallback

        seg = AlignedSegment(
            speaker="SPEAKER_00",
            text="buna ziua",
            start=0.0,
            end=1.0,
        )

        with patch.object(type(proc), "model", property(lambda self: None)):
            proc.process_segments([seg])

        assert seg.text[0].isupper()
