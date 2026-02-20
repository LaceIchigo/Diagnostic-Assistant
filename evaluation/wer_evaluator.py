"""Word Error Rate (WER) evaluator using jiwer."""

from dataclasses import dataclass
from typing import Dict, List, Optional

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class WERResult:
    """Word Error Rate evaluation results."""

    wer: float
    mer: float           # Match Error Rate
    wil: float           # Word Information Lost
    wip: float           # Word Information Preserved
    hits: int
    substitutions: int
    deletions: int
    insertions: int
    reference_length: int

    def __str__(self) -> str:
        return (
            f"WER={self.wer:.2%} | "
            f"S={self.substitutions} D={self.deletions} I={self.insertions} | "
            f"Ref={self.reference_length} words"
        )


class WEREvaluator:
    """Computes Word Error Rate and related metrics using jiwer.

    WER = (Substitutions + Deletions + Insertions) / N_reference
    """

    def __init__(
        self,
        normalize: bool = True,
        remove_punctuation: bool = True,
        lowercase: bool = True,
    ) -> None:
        """Initialize WEREvaluator.

        Args:
            normalize: Apply text normalization before computing WER.
            remove_punctuation: Strip punctuation for fairer comparison.
            lowercase: Convert both texts to lowercase.
        """
        self.normalize = normalize
        self.remove_punctuation = remove_punctuation
        self.lowercase = lowercase
        self._transform = None

    def _get_transform(self):
        """Build jiwer transform chain."""
        if self._transform is not None:
            return self._transform

        import jiwer  # type: ignore

        transforms = [jiwer.RemoveMultipleSpaces(), jiwer.Strip()]
        if self.lowercase:
            transforms.insert(0, jiwer.ToLowerCase())
        if self.remove_punctuation:
            transforms.insert(0, jiwer.RemovePunctuation())

        self._transform = jiwer.Compose(transforms)
        return self._transform

    def evaluate(self, reference: str, hypothesis: str) -> WERResult:
        """Compute WER between reference and hypothesis texts.

        Args:
            reference: Ground truth transcript.
            hypothesis: ASR system output.

        Returns:
            WERResult with detailed metrics.
        """
        import jiwer  # type: ignore

        transform = self._get_transform()
        measures = jiwer.compute_measures(
            reference,
            hypothesis,
            truth_transform=transform,
            hypothesis_transform=transform,
        )

        return WERResult(
            wer=measures["wer"],
            mer=measures["mer"],
            wil=measures["wil"],
            wip=measures["wip"],
            hits=measures["hits"],
            substitutions=measures["substitutions"],
            deletions=measures["deletions"],
            insertions=measures["insertions"],
            reference_length=measures["hits"] + measures["substitutions"] + measures["deletions"],
        )

    def evaluate_batch(
        self, references: List[str], hypotheses: List[str]
    ) -> Dict[str, WERResult]:
        """Evaluate WER for multiple reference-hypothesis pairs.

        Args:
            references: List of reference transcripts.
            hypotheses: List of hypothesis transcripts.

        Returns:
            Dict mapping index (as string) to WERResult.
        """
        if len(references) != len(hypotheses):
            raise ValueError("references and hypotheses must have the same length")

        results = {}
        for i, (ref, hyp) in enumerate(zip(references, hypotheses)):
            results[str(i)] = self.evaluate(ref, hyp)

        return results

    def evaluate_file(
        self, reference_path: str, hypothesis_path: str
    ) -> WERResult:
        """Compute WER from text files.

        Args:
            reference_path: Path to reference transcript file.
            hypothesis_path: Path to hypothesis transcript file.

        Returns:
            WERResult.
        """
        with open(reference_path, "r", encoding="utf-8") as f:
            reference = f.read()
        with open(hypothesis_path, "r", encoding="utf-8") as f:
            hypothesis = f.read()
        return self.evaluate(reference, hypothesis)

    def average_wer(self, results: Dict[str, WERResult]) -> float:
        """Compute macro-average WER across multiple results.

        Args:
            results: Dict of WERResult objects.

        Returns:
            Average WER.
        """
        if not results:
            return 0.0
        return sum(r.wer for r in results.values()) / len(results)
