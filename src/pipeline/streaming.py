"""Streaming/incremental pipeline with state management for real-time processing."""

import threading
import time
from collections import deque
from typing import Callable, Deque, List, Optional

import numpy as np

from diarization.alignment import AlignedSegment
from pipeline.orchestrator import PipelineConfig, PipelineOrchestrator, PipelineOutput
from utils.circular_buffer import CircularBuffer
from utils.logger import get_logger

logger = get_logger(__name__)


class StreamingPipeline:
    """Continuous streaming pipeline with state management.

    Processes audio in real-time from a CircularBuffer,
    maintaining context across processing windows.
    """

    def __init__(
        self,
        config: Optional[PipelineConfig] = None,
        on_output: Optional[Callable[[PipelineOutput], None]] = None,
        window_duration: float = 10.0,
        flush_interval: float = 2.0,
    ) -> None:
        """Initialize StreamingPipeline.

        Args:
            config: Pipeline configuration.
            on_output: Callback invoked with each PipelineOutput.
            window_duration: Duration of audio window to process at once (seconds).
            flush_interval: Seconds between processing attempts.
        """
        self.orchestrator = PipelineOrchestrator(config)
        self.on_output = on_output
        self.window_duration = window_duration
        self.flush_interval = flush_interval

        self._input_buffer: CircularBuffer = CircularBuffer(capacity=256)
        self._audio_accumulator = np.array([], dtype=np.float32)
        self._transcript_history: Deque[AlignedSegment] = deque(maxlen=1000)

        self._running = threading.Event()
        self._processing_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    @property
    def sample_rate(self) -> int:
        """Return sample rate from orchestrator config."""
        return self.orchestrator.config.sample_rate

    @property
    def window_samples(self) -> int:
        """Number of samples per processing window."""
        return int(self.window_duration * self.sample_rate)

    def push_audio(self, audio_chunk: np.ndarray) -> None:
        """Push a new audio chunk into the input buffer.

        Args:
            audio_chunk: 1-D numpy float32 array.
        """
        self._input_buffer.put(audio_chunk)

    def _processing_loop(self) -> None:
        """Background thread: reads chunks and processes windows."""
        logger.info("Streaming processing loop started.")

        while self._running.is_set():
            # Drain available chunks from input buffer
            while True:
                chunk = self._input_buffer.get(timeout=0.05)
                if chunk is None:
                    break
                with self._lock:
                    self._audio_accumulator = np.concatenate(
                        [self._audio_accumulator, chunk]
                    )

            # Process when we have enough audio
            with self._lock:
                acc_len = len(self._audio_accumulator)

            if acc_len >= self.window_samples:
                with self._lock:
                    window = self._audio_accumulator[: self.window_samples].copy()
                    # Keep overlap for context continuity
                    overlap_samples = int(
                        self.orchestrator.config.overlap * self.sample_rate
                    )
                    self._audio_accumulator = self._audio_accumulator[
                        self.window_samples - overlap_samples :
                    ]

                try:
                    output = self.orchestrator.process_audio(window)
                    if output.segments:
                        self._transcript_history.extend(output.segments)
                        if self.on_output:
                            self.on_output(output)
                except Exception as exc:
                    logger.error("Processing error: %s", exc, exc_info=True)
            else:
                time.sleep(self.flush_interval)

        logger.info("Streaming processing loop stopped.")

    def start(self) -> None:
        """Start the background processing thread."""
        if self._running.is_set():
            logger.warning("StreamingPipeline is already running.")
            return
        self._running.set()
        self._processing_thread = threading.Thread(
            target=self._processing_loop, daemon=True, name="streaming-pipeline"
        )
        self._processing_thread.start()
        logger.info("StreamingPipeline started.")

    def stop(self, timeout: float = 5.0) -> None:
        """Stop the background processing thread.

        Args:
            timeout: Maximum seconds to wait for thread to finish.
        """
        self._running.clear()
        if self._processing_thread is not None:
            self._processing_thread.join(timeout=timeout)
        logger.info("StreamingPipeline stopped.")

    @property
    def transcript(self) -> List[AlignedSegment]:
        """Return a copy of the current transcript history."""
        return list(self._transcript_history)

    @property
    def is_running(self) -> bool:
        """Return True if the processing loop is active."""
        return self._running.is_set()

    def __enter__(self) -> "StreamingPipeline":
        self.start()
        return self

    def __exit__(self, *args: object) -> None:
        self.stop()
