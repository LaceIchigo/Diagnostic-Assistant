"""Diarization Error Rate (DER) evaluator using pyannote.metrics."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DERResult:
    """Diarization Error Rate evaluation results."""

    der: float           # Total DER
    miss: float          # Missed speech
    false_alarm: float   # False alarm
    confusion: float     # Speaker confusion
    total_duration: float

    def __str__(self) -> str:
        return (
            f"DER={self.der:.2%} | "
            f"MISS={self.miss:.2%} FA={self.false_alarm:.2%} "
            f"CONF={self.confusion:.2%} | "
            f"Total={self.total_duration:.1f}s"
        )


def _build_annotation(turns: List[Tuple[float, float, str]]):
    """Build a pyannote Annotation from a list of (start, end, speaker) tuples."""
    from pyannote.core import Annotation, Segment  # type: ignore

    annotation = Annotation()
    for start, end, speaker in turns:
        annotation[Segment(start, end)] = speaker
    return annotation


class DEREvaluator:
    """Computes Diarization Error Rate using pyannote.metrics.

    DER = (Miss + False Alarm + Confusion) / Total Reference Speech Duration
    """

    def __init__(
        self,
        collar: float = 0.25,
        skip_overlap: bool = False,
    ) -> None:
        """Initialize DEREvaluator.

        Args:
            collar: Collar size in seconds around speaker changes (tolerance zone).
            skip_overlap: If True, skip overlapping regions in scoring.
        """
        self.collar = collar
        self.skip_overlap = skip_overlap
        self._metric = None

    def _get_metric(self):
        """Return pyannote DER metric (lazy initialization)."""
        if self._metric is not None:
            return self._metric
        from pyannote.metrics.diarization import DiarizationErrorRate  # type: ignore

        self._metric = DiarizationErrorRate(
            collar=self.collar,
            skip_overlap=self.skip_overlap,
        )
        return self._metric

    def evaluate(
        self,
        reference_turns: List[Tuple[float, float, str]],
        hypothesis_turns: List[Tuple[float, float, str]],
    ) -> DERResult:
        """Compute DER between reference and hypothesis speaker turns.

        Args:
            reference_turns: Ground truth as list of (start, end, speaker).
            hypothesis_turns: System output as list of (start, end, speaker).

        Returns:
            DERResult with detailed metrics.
        """
        from pyannote.metrics.diarization import DiarizationErrorRate  # type: ignore

        reference = _build_annotation(reference_turns)
        hypothesis = _build_annotation(hypothesis_turns)

        metric = DiarizationErrorRate(
            collar=self.collar, skip_overlap=self.skip_overlap
        )
        detailed = metric(reference, hypothesis, detailed=True)

        total_duration = sum(end - start for start, end, _ in reference_turns)

        return DERResult(
            der=detailed["diarization error rate"],
            miss=detailed["missed detection"] / total_duration if total_duration > 0 else 0.0,
            false_alarm=detailed["false alarm"] / total_duration if total_duration > 0 else 0.0,
            confusion=detailed["confusion"] / total_duration if total_duration > 0 else 0.0,
            total_duration=total_duration,
        )

    def evaluate_rttm(
        self, reference_rttm: str, hypothesis_rttm: str
    ) -> DERResult:
        """Compute DER from RTTM files.

        RTTM format: TYPE FILENAME CHANNEL ONSET DURATION <NA> <NA> SPEAKER <NA> <NA>

        Args:
            reference_rttm: Path to reference RTTM file.
            hypothesis_rttm: Path to hypothesis RTTM file.

        Returns:
            DERResult.
        """
        reference_turns = self._parse_rttm(reference_rttm)
        hypothesis_turns = self._parse_rttm(hypothesis_rttm)
        return self.evaluate(reference_turns, hypothesis_turns)

    @staticmethod
    def _parse_rttm(rttm_path: str) -> List[Tuple[float, float, str]]:
        """Parse an RTTM file into a list of (start, end, speaker) tuples."""
        turns = []
        with open(rttm_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith(";"):
                    continue
                parts = line.split()
                if len(parts) < 8 or parts[0] != "SPEAKER":
                    continue
                onset = float(parts[3])
                duration = float(parts[4])
                speaker = parts[7]
                turns.append((onset, onset + duration, speaker))
        return turns

    def average_der(self, results: Dict[str, DERResult]) -> float:
        """Compute macro-average DER across multiple results.

        Args:
            results: Dict of DERResult objects.

        Returns:
            Average DER.
        """
        if not results:
            return 0.0
        return sum(r.der for r in results.values()) / len(results)
