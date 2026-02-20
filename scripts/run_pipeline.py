#!/usr/bin/env python3
"""Entry point for the Diagnostic Assistant pipeline."""

import argparse
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dotenv import load_dotenv

load_dotenv()

from audio.capture import AudioCapture
from pipeline.orchestrator import PipelineConfig, PipelineOrchestrator
from postprocessing.role_labeling import MedicalRole
from utils.logger import get_logger, setup_logger


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Diagnostic Assistant — Real-time medical consultation transcription"
    )
    parser.add_argument(
        "--config",
        default="config/default.yaml",
        help="Path to YAML configuration file",
    )
    parser.add_argument(
        "--device-index",
        type=int,
        default=None,
        help="Audio input device index (see --list-devices)",
    )
    parser.add_argument(
        "--model-size",
        default="medium",
        choices=["tiny", "base", "small", "medium", "large-v2", "large-v3"],
        help="Whisper model size",
    )
    parser.add_argument(
        "--language",
        default="ro",
        help="Language code for transcription (default: ro)",
    )
    parser.add_argument(
        "--output-dir",
        default="./output",
        help="Directory to save transcripts",
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="List available audio input devices and exit",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )
    return parser.parse_args()


def main() -> None:
    """Run the Diagnostic Assistant pipeline."""
    args = parse_args()
    setup_logger(level=args.log_level)
    logger = get_logger(__name__)

    if args.list_devices:
        devices = AudioCapture.list_devices()
        print("Available audio input devices:")
        for d in devices:
            print(f"  [{d['index']}] {d['name']} ({d['channels']} channels)")
        return

    # Load config
    config = PipelineConfig(
        model_size=args.model_size,
        language=args.language,
        output_dir=args.output_dir,
    )
    if os.path.exists(args.config):
        orchestrator = PipelineOrchestrator.from_yaml(args.config)
        orchestrator.config.model_size = args.model_size
        orchestrator.config.language = args.language
        orchestrator.config.output_dir = args.output_dir
    else:
        orchestrator = PipelineOrchestrator(config=config)
        logger.warning("Config file not found: %s. Using defaults.", args.config)

    os.makedirs(args.output_dir, exist_ok=True)

    # Start capture
    capture = AudioCapture(
        sample_rate=orchestrator.config.sample_rate,
        device_index=args.device_index,
        chunk_duration=orchestrator.config.chunk_duration,
    )

    logger.info("=" * 60)
    logger.info("Diagnostic Assistant — Pipeline Started")
    logger.info("Model: %s | Language: %s", args.model_size, args.language)
    logger.info("Output: %s", args.output_dir)
    logger.info("Press Ctrl+C to stop.")
    logger.info("=" * 60)

    all_segments = []

    try:
        with capture:
            while True:
                chunk = capture.read_chunk(timeout=2.0)
                if chunk is None:
                    continue

                output = orchestrator.process_audio(chunk)
                all_segments.extend(output.segments)

                for seg in output.segments:
                    role = getattr(seg, "role", MedicalRole.UNKNOWN)
                    print(
                        f"[{seg.start:.1f}s–{seg.end:.1f}s] "
                        f"{role.value}: {seg.text}"
                    )

    except KeyboardInterrupt:
        logger.info("Stopping pipeline...")

    finally:
        # Save transcript
        if all_segments:
            from pipeline.orchestrator import PipelineOutput
            output = PipelineOutput(segments=all_segments)
            saved_path = orchestrator.save_output(output)
            print(f"\nTranscript saved to: {saved_path}")


if __name__ == "__main__":
    main()
