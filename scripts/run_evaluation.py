#!/usr/bin/env python3
"""Run evaluation suite for WER and DER metrics."""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv()

from evaluation.incremental_test import IncrementalTestRunner
from utils.logger import get_logger, setup_logger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diagnostic Assistant — Evaluation Suite"
    )
    parser.add_argument(
        "--test-dir",
        default="evaluation/datasets",
        help="Directory containing test scenarios",
    )
    parser.add_argument(
        "--output",
        default="results",
        help="Output directory for results",
    )
    parser.add_argument(
        "--scenario",
        default=None,
        help="Run a specific scenario ID (e.g., 01_baseline). Default: all.",
    )
    parser.add_argument(
        "--with-pipeline",
        action="store_true",
        help="Initialize and use the full pipeline for ASR evaluation",
    )
    parser.add_argument(
        "--model-size",
        default="medium",
        help="Whisper model size for pipeline evaluation",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    setup_logger(level=args.log_level)
    logger = get_logger(__name__)

    logger.info("Starting evaluation suite...")
    logger.info("Test dir: %s", args.test_dir)
    logger.info("Output: %s", args.output)

    pipeline = None
    if args.with_pipeline:
        from pipeline.orchestrator import PipelineConfig, PipelineOrchestrator

        config = PipelineConfig(model_size=args.model_size, language="ro")
        pipeline = PipelineOrchestrator(config=config)
        logger.info("Pipeline initialized with model: %s", args.model_size)

    runner = IncrementalTestRunner(
        test_dir=args.test_dir,
        output_dir=args.output,
    )

    if args.scenario:
        from evaluation.incremental_test import INCREMENTAL_SCENARIOS

        matching = [s for s in INCREMENTAL_SCENARIOS if s.scenario_id == args.scenario]
        if not matching:
            logger.error("Scenario not found: %s", args.scenario)
            sys.exit(1)
        results = [runner.run_scenario(matching[0], pipeline=pipeline)]
        runner._save_results(results)
        runner._print_summary(results)
    else:
        results = runner.run_all(pipeline=pipeline)

    passed = sum(1 for r in results if r.passed)
    total = len(results)
    print(f"\nEvaluation complete: {passed}/{total} scenarios passed.")

    if passed < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
