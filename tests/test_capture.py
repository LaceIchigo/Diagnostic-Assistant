"""Tests for audio capture module using mocked sounddevice."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import threading
import time
from unittest.mock import MagicMock

import numpy as np
import pytest

from audio.capture import AudioCapture
from utils.circular_buffer import CircularBuffer


class TestCircularBuffer:
    """Tests for the CircularBuffer utility used by AudioCapture."""

    def test_put_and_get(self):
        buf = CircularBuffer(capacity=4)
        arr = np.zeros(100)
        buf.put(arr)
        result = buf.get(timeout=0.1)
        assert result is not None
        np.testing.assert_array_equal(result, arr)

    def test_overflow_drops_oldest(self):
        buf = CircularBuffer(capacity=2)
        buf.put(np.array([1.0]))
        buf.put(np.array([2.0]))
        buf.put(np.array([3.0]))  # Should overflow and drop item 1
        assert buf.dropped_count >= 1

    def test_get_timeout(self):
        buf = CircularBuffer(capacity=4)
        result = buf.get(timeout=0.05)
        assert result is None

    def test_size(self):
        buf = CircularBuffer(capacity=4)
        assert buf.size == 0
        buf.put(np.zeros(10))
        assert buf.size == 1

    def test_clear(self):
        buf = CircularBuffer(capacity=4)
        buf.put(np.zeros(10))
        buf.put(np.zeros(10))
        buf.clear()
        assert buf.is_empty

    def test_thread_safety(self):
        buf = CircularBuffer(capacity=100)
        results = []
        errors = []

        def producer():
            for i in range(50):
                buf.put(np.array([float(i)]))
                time.sleep(0.001)

        def consumer():
            count = 0
            while count < 50:
                item = buf.get(timeout=0.5)
                if item is not None:
                    results.append(item[0])
                    count += 1

        t1 = threading.Thread(target=producer)
        t2 = threading.Thread(target=consumer)
        t1.start()
        t2.start()
        t1.join(timeout=5)
        t2.join(timeout=5)
        assert len(results) == 50


class TestAudioCapture:
    """Tests for AudioCapture using mocked sounddevice."""

    def test_start_creates_stream(self):
        import sounddevice as sd
        mock_stream = MagicMock()
        sd.InputStream.return_value = mock_stream

        capture = AudioCapture(sample_rate=16000, chunk_duration=0.1)
        capture.start()

        sd.InputStream.assert_called()
        mock_stream.start.assert_called_once()
        assert capture.is_running
        capture.stop()

    def test_stop_closes_stream(self):
        import sounddevice as sd
        mock_stream = MagicMock()
        sd.InputStream.return_value = mock_stream

        capture = AudioCapture(sample_rate=16000, chunk_duration=0.1)
        capture.start()
        capture.stop()

        mock_stream.stop.assert_called_once()
        mock_stream.close.assert_called_once()
        assert not capture.is_running

    def test_callback_accumulates_and_chunks(self):
        chunk_duration = 0.5
        sample_rate = 16000
        chunk_samples = int(chunk_duration * sample_rate)

        received_chunks = []
        capture = AudioCapture(
            sample_rate=sample_rate,
            chunk_duration=chunk_duration,
            on_chunk=received_chunks.append,
        )

        # Simulate callback with enough audio to produce 2 chunks
        audio_data = np.zeros((chunk_samples * 2, 1), dtype=np.float32)
        status = MagicMock()
        status.__bool__ = lambda self: False
        capture._callback(audio_data, len(audio_data), None, status)

        assert len(received_chunks) == 2
        assert len(received_chunks[0]) == chunk_samples

    def test_context_manager(self):
        import sounddevice as sd
        mock_stream = MagicMock()
        sd.InputStream.return_value = mock_stream

        with AudioCapture(sample_rate=16000, chunk_duration=0.1) as capture:
            assert capture.is_running

        assert not capture.is_running

    def test_list_devices(self):
        devices = AudioCapture.list_devices()
        # conftest.py provides 2 input devices
        assert isinstance(devices, list)
        assert len(devices) >= 1
