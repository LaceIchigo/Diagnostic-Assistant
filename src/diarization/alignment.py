"""Alignment of ASR transcription with diarization speaker turns."""

from dataclasses import dataclass, field
from typing import List, Optional

from asr.whisper_asr import TranscribedSegment, WordTimestamp
from diarization.pyannote_diar import SpeakerTurn
from utils.logger import get_logger
from utils.timestamp_utils import compute_overlap

logger = get_logger(__name__)


@dataclass
class AlignedSegment:
    """A transcribed segment aligned with a speaker identity."""

    speaker: str
    text: str
    start: float
    end: float
    words: List[WordTimestamp] = field(default_factory=list)

    @property
    def duration(self) -> float:
        """Segment duration in seconds."""
        return self.end - self.start


class DiarizationAligner:
    """Aligns ASR transcript segments with diarization speaker turns.

    Uses timestamp overlap to assign each transcribed segment to the
    speaker turn with the maximum temporal overlap.
    """

    def __init__(self, unknown_speaker_label: str = "SPEAKER_UNKNOWN") -> None:
        """Initialize DiarizationAligner.

        Args:
            unknown_speaker_label: Label used when no speaker turn overlaps
                                   with a transcribed segment.
        """
        self.unknown_speaker_label = unknown_speaker_label

    def align(
        self,
        asr_segments: List[TranscribedSegment],
        speaker_turns: List[SpeakerTurn],
    ) -> List[AlignedSegment]:
        """Align ASR segments with speaker turns.

        Each ASR segment is assigned to the speaker with the maximum
        temporal overlap with that segment.

        Args:
            asr_segments: List of TranscribedSegment from ASR.
            speaker_turns: List of SpeakerTurn from diarization.

        Returns:
            List of AlignedSegment sorted by start time.
        """
        aligned = []

        for seg in asr_segments:
            speaker = self._find_best_speaker(seg, speaker_turns)
            aligned.append(
                AlignedSegment(
                    speaker=speaker,
                    text=seg.text,
                    start=seg.start,
                    end=seg.end,
                    words=seg.words,
                )
            )

        return sorted(aligned, key=lambda s: s.start)

    def _find_best_speaker(
        self,
        segment: TranscribedSegment,
        speaker_turns: List[SpeakerTurn],
    ) -> str:
        """Find the speaker with maximum overlap with the given ASR segment.

        Args:
            segment: ASR transcribed segment.
            speaker_turns: List of diarization speaker turns.

        Returns:
            Speaker identifier string.
        """
        best_speaker = self.unknown_speaker_label
        best_overlap = 0.0

        for turn in speaker_turns:
            overlap = compute_overlap(
                (segment.start, segment.end),
                (turn.start, turn.end),
            )
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = turn.speaker

        return best_speaker

    def align_word_level(
        self,
        asr_segments: List[TranscribedSegment],
        speaker_turns: List[SpeakerTurn],
    ) -> List[AlignedSegment]:
        """Align at word level for finer-grained speaker attribution.

        Groups consecutive words attributed to the same speaker into segments.

        Args:
            asr_segments: List of TranscribedSegment with word timestamps.
            speaker_turns: List of SpeakerTurn from diarization.

        Returns:
            List of AlignedSegment sorted by start time.
        """
        # Flatten all words
        all_words: List[WordTimestamp] = []
        for seg in asr_segments:
            all_words.extend(seg.words)

        if not all_words:
            return self.align(asr_segments, speaker_turns)

        # Assign each word to a speaker
        word_speakers = []
        for word in all_words:
            word_mid = (word.start + word.end) / 2
            speaker = self._point_speaker(word_mid, speaker_turns)
            word_speakers.append((word, speaker))

        # Group consecutive words by speaker
        aligned = []
        if not word_speakers:
            return aligned

        current_speaker = word_speakers[0][1]
        current_words = [word_speakers[0][0]]

        for word, speaker in word_speakers[1:]:
            if speaker == current_speaker:
                current_words.append(word)
            else:
                aligned.append(self._words_to_segment(current_words, current_speaker))
                current_speaker = speaker
                current_words = [word]

        if current_words:
            aligned.append(self._words_to_segment(current_words, current_speaker))

        return aligned

    def _point_speaker(
        self, time_point: float, speaker_turns: List[SpeakerTurn]
    ) -> str:
        """Find the speaker active at a specific time point."""
        for turn in speaker_turns:
            if turn.start <= time_point <= turn.end:
                return turn.speaker
        return self.unknown_speaker_label

    @staticmethod
    def _words_to_segment(
        words: List[WordTimestamp], speaker: str
    ) -> AlignedSegment:
        """Create an AlignedSegment from a list of words."""
        text = "".join(w.word for w in words).strip()
        return AlignedSegment(
            speaker=speaker,
            text=text,
            start=words[0].start,
            end=words[-1].end,
            words=words,
        )
