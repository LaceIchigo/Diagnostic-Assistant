"""Audio preprocessing: noise reduction, normalization, and resampling."""

from typing import Optional

import numpy as np
import scipy.signal


class AudioPreprocessor:
    """Preprocesses raw audio for ASR/VAD pipelines.

    Applies:
    - Resampling to 16 kHz (required by Whisper and Silero VAD)
    - Spectral gating noise reduction
    - Amplitude normalization
    """

    def __init__(
        self,
        target_sample_rate: int = 16000,
        normalize: bool = True,
        noise_reduce: bool = True,
    ) -> None:
        """Initialize AudioPreprocessor.

        Args:
            target_sample_rate: Target sample rate in Hz (default 16000).
            normalize: Whether to normalize audio amplitude.
            noise_reduce: Whether to apply spectral gating noise reduction.
        """
        self.target_sample_rate = target_sample_rate
        self.normalize = normalize
        self.noise_reduce = noise_reduce

    def process(
        self,
        audio: np.ndarray,
        source_sample_rate: int,
    ) -> np.ndarray:
        """Apply full preprocessing pipeline to an audio array.

        Args:
            audio: 1-D numpy float32 array of audio samples.
            source_sample_rate: Sample rate of the input audio.

        Returns:
            Preprocessed 1-D numpy float32 array at target_sample_rate.
        """
        audio = audio.astype(np.float32)

        if source_sample_rate != self.target_sample_rate:
            audio = self.resample(audio, source_sample_rate, self.target_sample_rate)

        if self.noise_reduce:
            audio = self._spectral_gate(audio)

        if self.normalize:
            audio = self._normalize(audio)

        return audio

    def resample(
        self,
        audio: np.ndarray,
        source_rate: int,
        target_rate: int,
    ) -> np.ndarray:
        """Resample audio to a new sample rate.

        Args:
            audio: Input audio array.
            source_rate: Original sample rate.
            target_rate: Target sample rate.

        Returns:
            Resampled audio array.
        """
        if source_rate == target_rate:
            return audio
        num_samples = int(len(audio) * target_rate / source_rate)
        return scipy.signal.resample(audio, num_samples).astype(np.float32)

    @staticmethod
    def _normalize(audio: np.ndarray) -> np.ndarray:
        """Normalize audio to [-1, 1] range using peak normalization."""
        peak = np.max(np.abs(audio))
        if peak > 0:
            return audio / peak
        return audio

    @staticmethod
    def _spectral_gate(
        audio: np.ndarray,
        n_fft: int = 512,
        threshold_multiplier: float = 1.5,
    ) -> np.ndarray:
        """Apply simple spectral gating for noise reduction.

        Estimates noise floor from the first 0.5 seconds and attenuates
        frequency bins below the noise threshold.

        Args:
            audio: Input audio array (float32).
            n_fft: FFT window size.
            threshold_multiplier: Multiplier for noise floor threshold.

        Returns:
            Denoised audio array.
        """
        hop_length = n_fft // 4
        # Estimate noise profile from initial silence (first 0.5s at 16kHz = 8000 samples)
        noise_sample_len = min(8000, len(audio) // 4)
        noise_sample = audio[:noise_sample_len]

        # Compute STFT of noise sample
        _, _, noise_stft = scipy.signal.stft(
            noise_sample, nperseg=n_fft, noverlap=n_fft - hop_length
        )
        noise_magnitude = np.mean(np.abs(noise_stft), axis=1, keepdims=True)

        # Compute STFT of full audio
        freqs, times, stft = scipy.signal.stft(
            audio, nperseg=n_fft, noverlap=n_fft - hop_length
        )
        magnitude = np.abs(stft)
        phase = np.angle(stft)

        # Apply spectral gate
        threshold = noise_magnitude * threshold_multiplier
        mask = magnitude > threshold
        cleaned_magnitude = magnitude * mask

        # Reconstruct signal
        cleaned_stft = cleaned_magnitude * np.exp(1j * phase)
        _, cleaned_audio = scipy.signal.istft(
            cleaned_stft, nperseg=n_fft, noverlap=n_fft - hop_length
        )

        # Match output length to input
        if len(cleaned_audio) > len(audio):
            cleaned_audio = cleaned_audio[: len(audio)]
        elif len(cleaned_audio) < len(audio):
            cleaned_audio = np.pad(cleaned_audio, (0, len(audio) - len(cleaned_audio)))

        return cleaned_audio.astype(np.float32)
