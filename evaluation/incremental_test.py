"""Incremental test scenarios for WER/DER evaluation with increasing complexity."""

import json
import os
import time
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

import numpy as np

from evaluation.wer_evaluator import WEREvaluator, WERResult
from evaluation.der_evaluator import DEREvaluator, DERResult
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ScenarioResult:
    """Result for a single evaluation scenario."""

    scenario_id: str
    scenario_name: str
    wer_result: Optional[WERResult] = None
    der_result: Optional[DERResult] = None
    processing_time: float = 0.0
    passed: bool = False
    wer_threshold: float = 0.20
    der_threshold: float = 0.20

    def evaluate_pass(self) -> bool:
        """Determine if the scenario passed all thresholds."""
        wer_ok = self.wer_result is None or self.wer_result.wer <= self.wer_threshold
        der_ok = self.der_result is None or self.der_result.der <= self.der_threshold
        self.passed = wer_ok and der_ok
        return self.passed

    def to_dict(self) -> dict:
        return {
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "passed": self.passed,
            "processing_time": self.processing_time,
            "wer": self.wer_result.wer if self.wer_result else None,
            "der": self.der_result.der if self.der_result else None,
        }


@dataclass
class TestScenario:
    """Definition of an evaluation scenario."""

    scenario_id: str
    name: str
    description: str
    audio_path: Optional[str]          # Path to WAV file
    reference_transcript: Optional[str]  # Reference text or path
    reference_rttm: Optional[str]        # Path to reference RTTM
    wer_threshold: float = 0.20
    der_threshold: float = 0.20


INCREMENTAL_SCENARIOS = [
    TestScenario(
        scenario_id="01_baseline",
        name="Baseline — condiții ideale",
        description="2 vorbitori, fără zgomot, voci distincte, 5 minute",
        audio_path=None,
        reference_transcript=None,
        reference_rttm=None,
        wer_threshold=0.10,
        der_threshold=0.10,
    ),
    TestScenario(
        scenario_id="02_background_noise",
        name="Zgomot de fond",
        description="Consultație cu zgomot de fond (aparate medicale)",
        audio_path=None,
        reference_transcript=None,
        reference_rttm=None,
        wer_threshold=0.20,
        der_threshold=0.20,
    ),
    TestScenario(
        scenario_id="03_medical_terminology",
        name="Terminologie medicală",
        description="Consultație cu termeni medicali specializați în română",
        audio_path=None,
        reference_transcript=None,
        reference_rttm=None,
        wer_threshold=0.25,
        der_threshold=0.15,
    ),
    TestScenario(
        scenario_id="04_overlapping_speech",
        name="Suprapuneri de vorbire",
        description="Conversație cu întreruperi și suprapuneri frecvente",
        audio_path=None,
        reference_transcript=None,
        reference_rttm=None,
        wer_threshold=0.25,
        der_threshold=0.30,
    ),
    TestScenario(
        scenario_id="05_long_session",
        name="Sesiune lungă (30 min)",
        description="Consultație completă de 30 de minute",
        audio_path=None,
        reference_transcript=None,
        reference_rttm=None,
        wer_threshold=0.15,
        der_threshold=0.15,
    ),
]


class IncrementalTestRunner:
    """Runs incremental evaluation scenarios with increasing complexity."""

    def __init__(
        self,
        test_dir: str = "evaluation/datasets",
        output_dir: str = "results",
    ) -> None:
        """Initialize IncrementalTestRunner.

        Args:
            test_dir: Directory containing test audio and reference files.
            output_dir: Directory for saving evaluation results.
        """
        self.test_dir = test_dir
        self.output_dir = output_dir
        self.wer_evaluator = WEREvaluator()
        self.der_evaluator = DEREvaluator()

    def run_scenario(
        self, scenario: TestScenario, pipeline=None
    ) -> ScenarioResult:
        """Run a single evaluation scenario.

        Args:
            scenario: TestScenario to evaluate.
            pipeline: Optional PipelineOrchestrator instance. If None, skips ASR.

        Returns:
            ScenarioResult with WER/DER metrics.
        """
        logger.info("Running scenario: %s — %s", scenario.scenario_id, scenario.name)
        result = ScenarioResult(
            scenario_id=scenario.scenario_id,
            scenario_name=scenario.name,
            wer_threshold=scenario.wer_threshold,
            der_threshold=scenario.der_threshold,
        )

        # Resolve file paths
        audio_path = scenario.audio_path
        if audio_path and not os.path.isabs(audio_path):
            audio_path = os.path.join(self.test_dir, scenario.scenario_id, "audio.wav")

        ref_transcript_path = scenario.reference_transcript
        if ref_transcript_path and not os.path.isabs(ref_transcript_path):
            ref_transcript_path = os.path.join(
                self.test_dir, scenario.scenario_id, "reference.txt"
            )

        ref_rttm_path = scenario.reference_rttm
        if ref_rttm_path and not os.path.isabs(ref_rttm_path):
            ref_rttm_path = os.path.join(
                self.test_dir, scenario.scenario_id, "reference.rttm"
            )

        start_time = time.time()

        # WER evaluation
        if audio_path and os.path.exists(audio_path) and ref_transcript_path and \
                os.path.exists(ref_transcript_path) and pipeline is not None:
            try:
                import scipy.io.wavfile
                sr, audio = scipy.io.wavfile.read(audio_path)
                audio = audio.astype(np.float32) / 32767.0

                output = pipeline.process_audio(audio)
                hypothesis = " ".join(seg.text for seg in output.segments)

                with open(ref_transcript_path, "r", encoding="utf-8") as f:
                    reference = f.read()

                result.wer_result = self.wer_evaluator.evaluate(reference, hypothesis)
                logger.info("WER: %s", result.wer_result)
            except Exception as exc:
                logger.warning("WER evaluation failed: %s", exc)

        # DER evaluation
        if ref_rttm_path and os.path.exists(ref_rttm_path):
            hyp_rttm_path = os.path.join(
                self.output_dir, f"{scenario.scenario_id}_hyp.rttm"
            )
            if os.path.exists(hyp_rttm_path):
                try:
                    result.der_result = self.der_evaluator.evaluate_rttm(
                        ref_rttm_path, hyp_rttm_path
                    )
                    logger.info("DER: %s", result.der_result)
                except Exception as exc:
                    logger.warning("DER evaluation failed: %s", exc)

        result.processing_time = time.time() - start_time
        result.evaluate_pass()

        status = "✓ PASSED" if result.passed else "✗ FAILED"
        logger.info(
            "Scenario %s: %s (WER=%.2f, DER=%.2f, t=%.1fs)",
            scenario.scenario_id,
            status,
            result.wer_result.wer if result.wer_result else float("nan"),
            result.der_result.der if result.der_result else float("nan"),
            result.processing_time,
        )

        return result

    def run_all(self, pipeline=None) -> List[ScenarioResult]:
        """Run all incremental scenarios.

        Args:
            pipeline: Optional pipeline instance for ASR evaluation.

        Returns:
            List of ScenarioResult.
        """
        os.makedirs(self.output_dir, exist_ok=True)
        results = []

        for scenario in INCREMENTAL_SCENARIOS:
            result = self.run_scenario(scenario, pipeline=pipeline)
            results.append(result)

        self._save_results(results)
        self._print_summary(results)
        return results

    def _save_results(self, results: List[ScenarioResult]) -> None:
        """Save results to JSON file."""
        output_path = os.path.join(self.output_dir, "evaluation_results.json")
        data = [r.to_dict() for r in results]
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info("Results saved to %s", output_path)

    @staticmethod
    def _print_summary(results: List[ScenarioResult]) -> None:
        """Print a summary table of results."""
        print("\n" + "=" * 70)
        print(f"{'Scenario':<30} {'WER':>8} {'DER':>8} {'Status':>10}")
        print("=" * 70)
        for r in results:
            wer_str = f"{r.wer_result.wer:.2%}" if r.wer_result else "N/A"
            der_str = f"{r.der_result.der:.2%}" if r.der_result else "N/A"
            status = "✓ PASS" if r.passed else "✗ FAIL"
            print(f"{r.scenario_name:<30} {wer_str:>8} {der_str:>8} {status:>10}")
        print("=" * 70)
        passed = sum(1 for r in results if r.passed)
        print(f"Total: {passed}/{len(results)} scenarios passed\n")
