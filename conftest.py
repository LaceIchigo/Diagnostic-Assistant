"""Pytest configuration: set up sys.path and mock unavailable heavy dependencies."""

import sys
import os
from unittest.mock import MagicMock

# Add src directory to sys.path so tests can import from src/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Mock sounddevice (not available in CI environment)
_mock_sd = MagicMock()
_mock_sd.query_devices.return_value = [
    {"name": "Microphone", "max_input_channels": 2},
    {"name": "Default", "max_input_channels": 1},
]
_mock_sd.InputStream.return_value = MagicMock()
sys.modules.setdefault("sounddevice", _mock_sd)

# Mock torch (GPU not available in CI environment)
# IMPORTANT: torch.Tensor must be a real class to avoid breaking scipy's issubclass check


class _FakeTensor:
    """Minimal fake Tensor class."""
    pass


class _MockCuda:
    @staticmethod
    def is_available():
        return False


class _MockHub:
    @staticmethod
    def load(*args, **kwargs):
        return (MagicMock(), (MagicMock(),))


class _MockNoGrad:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _mock_from_numpy(arr):
    m = MagicMock()
    m.item.return_value = 0.5
    m.dim.return_value = 1
    m.unsqueeze.return_value = m
    m.to.return_value = m
    return m


_mock_torch = MagicMock()
_mock_torch.Tensor = _FakeTensor
_mock_torch.cuda = _MockCuda()
_mock_torch.hub = _MockHub()
_mock_torch.no_grad.return_value = _MockNoGrad()
_mock_torch.from_numpy.side_effect = _mock_from_numpy
_mock_torch.device = lambda s: s

sys.modules.setdefault("torch", _mock_torch)
sys.modules.setdefault("torch.nn", MagicMock())

# Mock faster_whisper (not installed in CI)
sys.modules.setdefault("faster_whisper", MagicMock())

# Mock pyannote modules (not installed in CI)
sys.modules.setdefault("pyannote", MagicMock())
sys.modules.setdefault("pyannote.audio", MagicMock())
sys.modules.setdefault("pyannote.core", MagicMock())
sys.modules.setdefault("pyannote.metrics", MagicMock())
sys.modules.setdefault("pyannote.metrics.diarization", MagicMock())

# Mock deepmultilingualpunctuation (not installed in CI)
sys.modules.setdefault("deepmultilingualpunctuation", MagicMock())
