"""Timestamp utilities for overlap calculation, conversion, and segment merging."""

from dataclasses import dataclass
from typing import List, Tuple


def compute_overlap(
    interval_a: Tuple[float, float],
    interval_b: Tuple[float, float],
) -> float:
    """Compute the overlap duration between two time intervals.

    Args:
        interval_a: (start, end) in seconds.
        interval_b: (start, end) in seconds.

    Returns:
        Overlap duration in seconds (0 if no overlap).
    """
    start = max(interval_a[0], interval_b[0])
    end = min(interval_a[1], interval_b[1])
    return max(0.0, end - start)


def compute_iou(
    interval_a: Tuple[float, float],
    interval_b: Tuple[float, float],
) -> float:
    """Compute Intersection over Union (IoU) for two time intervals.

    Args:
        interval_a: (start, end) in seconds.
        interval_b: (start, end) in seconds.

    Returns:
        IoU score in [0, 1].
    """
    intersection = compute_overlap(interval_a, interval_b)
    if intersection == 0.0:
        return 0.0
    union = (interval_a[1] - interval_a[0]) + (interval_b[1] - interval_b[0]) - intersection
    return intersection / union if union > 0 else 0.0


def seconds_to_hms(seconds: float) -> str:
    """Convert seconds to HH:MM:SS.mmm format.

    Args:
        seconds: Time in seconds.

    Returns:
        Formatted string like "00:01:23.456".
    """
    ms = int((seconds % 1) * 1000)
    total_s = int(seconds)
    s = total_s % 60
    m = (total_s // 60) % 60
    h = total_s // 3600
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def hms_to_seconds(hms: str) -> float:
    """Convert HH:MM:SS.mmm format to seconds.

    Args:
        hms: String in format "HH:MM:SS.mmm" or "MM:SS.mmm".

    Returns:
        Total seconds as float.
    """
    parts = hms.split(":")
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    return float(hms)


@dataclass
class TimeSegment:
    """Generic time segment with start and end."""

    start: float
    end: float
    label: str = ""

    @property
    def duration(self) -> float:
        """Duration in seconds."""
        return self.end - self.start


def merge_segments(
    segments: List[TimeSegment],
    gap_threshold: float = 0.1,
) -> List[TimeSegment]:
    """Merge consecutive segments with the same label and small gap.

    Args:
        segments: List of TimeSegment sorted by start time.
        gap_threshold: Maximum gap between segments to merge (seconds).

    Returns:
        Merged list of TimeSegment.
    """
    if not segments:
        return segments

    segments = sorted(segments, key=lambda s: s.start)
    merged = [TimeSegment(segments[0].start, segments[0].end, segments[0].label)]

    for seg in segments[1:]:
        last = merged[-1]
        if seg.label == last.label and seg.start - last.end <= gap_threshold:
            merged[-1] = TimeSegment(last.start, max(last.end, seg.end), last.label)
        else:
            merged.append(TimeSegment(seg.start, seg.end, seg.label))

    return merged


def samples_to_seconds(samples: int, sample_rate: int) -> float:
    """Convert sample count to time in seconds.

    Args:
        samples: Number of audio samples.
        sample_rate: Sample rate in Hz.

    Returns:
        Time in seconds.
    """
    return samples / sample_rate


def seconds_to_samples(seconds: float, sample_rate: int) -> int:
    """Convert time in seconds to sample count.

    Args:
        seconds: Time in seconds.
        sample_rate: Sample rate in Hz.

    Returns:
        Number of samples.
    """
    return int(seconds * sample_rate)
