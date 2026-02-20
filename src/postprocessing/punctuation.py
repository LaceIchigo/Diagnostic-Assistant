"""Punctuation and capitalization restoration using deepmultilingualpunctuation."""

from typing import List, Optional

from utils.logger import get_logger

logger = get_logger(__name__)


class PunctuationProcessor:
    """Restores punctuation and capitalization in raw ASR output.

    Uses deepmultilingualpunctuation which supports Romanian text.
    """

    def __init__(
        self,
        model_name: str = "oliverguhr/fullstop-punctuation-multilang-large",
        language: str = "ro",
        device: str = "cuda",
        batch_size: int = 32,
        overlap_size: int = 10,
    ) -> None:
        """Initialize PunctuationProcessor.

        Args:
            model_name: HuggingFace model name for punctuation restoration.
            language: Language code for punctuation model.
            device: PyTorch device ("cuda" for ROCm, "cpu" for fallback).
            batch_size: Batch size for processing.
            overlap_size: Token overlap between batches for long texts.
        """
        self.model_name = model_name
        self.language = language
        self.device = device
        self.batch_size = batch_size
        self.overlap_size = overlap_size
        self._model = None

    def load(self) -> None:
        """Load the punctuation model."""
        try:
            from deepmultilingualpunctuation import PunctuationModel  # type: ignore

            logger.info("Loading punctuation model: %s", self.model_name)
            self._model = PunctuationModel(model=self.model_name)
            logger.info("Punctuation model loaded.")
        except ImportError:
            logger.warning(
                "deepmultilingualpunctuation not available, using fallback processor"
            )
            self._model = None

    @property
    def model(self):
        """Return the loaded model, loading if necessary."""
        if self._model is None:
            self.load()
        return self._model

    def add_punctuation(self, text: str) -> str:
        """Add punctuation and capitalization to a text string.

        Args:
            text: Raw ASR output text without punctuation.

        Returns:
            Text with punctuation and capitalization restored.
        """
        if not text or not text.strip():
            return text

        if self.model is None:
            return self._fallback_punctuation(text)

        try:
            result = self.model.restore_punctuation(text)
            return result
        except Exception as exc:
            logger.warning("Punctuation model failed: %s. Using fallback.", exc)
            return self._fallback_punctuation(text)

    def process_segments(self, segments: list) -> list:
        """Apply punctuation to a list of AlignedSegment objects.

        Args:
            segments: List of AlignedSegment (must have .text attribute).

        Returns:
            Updated list with punctuated text.
        """
        for seg in segments:
            seg.text = self.add_punctuation(seg.text)
        return segments

    @staticmethod
    def _fallback_punctuation(text: str) -> str:
        """Simple fallback: capitalize first letter and add period if missing."""
        text = text.strip()
        if not text:
            return text
        text = text[0].upper() + text[1:]
        if text[-1] not in ".!?,;:":
            text += "."
        return text
