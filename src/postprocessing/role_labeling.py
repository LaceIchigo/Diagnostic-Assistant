"""Role labeling: maps speaker IDs to Doctor/Patient roles."""

from enum import Enum
from typing import Dict, List, Optional

from utils.logger import get_logger

logger = get_logger(__name__)


class MedicalRole(str, Enum):
    """Medical roles in a consultation."""

    DOCTOR = "Doctor"
    PATIENT = "Pacient"
    UNKNOWN = "Necunoscut"


# Romanian medical question keywords typical for doctors
DOCTOR_KEYWORDS = {
    "durere", "simptome", "diagnostic", "tratament", "medicament",
    "consultație", "analize", "investigații", "tensiune", "temperatură",
    "reteta", "rețetă", "prescriu", "recomand", "examinare", "ausculta",
    "deschideți", "respirați", "înghițiți", "istoricul", "antecedente",
    "alergii", "operații", "internare", "spital", "specialist", "trimitere",
}

# Romanian keywords typical for patients
PATIENT_KEYWORDS = {
    "mă doare", "simt", "am", "nu pot", "de când", "zile", "săptămâni",
    "obosit", "febră", "tuse", "greață", "amețeală", "durere", "rău",
    "pastile", "medicamentele", "tratamentul", "mulțumesc",
}


class RoleLabeler:
    """Maps diarization speaker IDs to Doctor/Patient roles.

    Uses a combination of:
    1. Explicit speaker-to-role mapping (if provided)
    2. Keyword-based heuristics for Romanian medical consultations
    3. Speaking-time heuristic (Doctor typically speaks more in consultations)
    """

    def __init__(
        self,
        speaker_role_map: Optional[Dict[str, MedicalRole]] = None,
        doctor_speaker: Optional[str] = None,
    ) -> None:
        """Initialize RoleLabeler.

        Args:
            speaker_role_map: Explicit mapping from speaker ID to MedicalRole.
                              If provided, this takes precedence over heuristics.
            doctor_speaker: If known, the speaker ID corresponding to the doctor.
        """
        self.speaker_role_map: Dict[str, MedicalRole] = speaker_role_map or {}
        if doctor_speaker and doctor_speaker not in self.speaker_role_map:
            self.speaker_role_map[doctor_speaker] = MedicalRole.DOCTOR

    def label_segments(self, segments: list) -> list:
        """Apply role labels to a list of AlignedSegment objects.

        If no explicit mapping is available, infers roles from heuristics
        and updates the internal speaker_role_map for consistency.

        Args:
            segments: List of AlignedSegment (must have .speaker and .text attributes).

        Returns:
            Updated segments with a .role attribute added.
        """
        if not self.speaker_role_map:
            self._infer_roles(segments)

        for seg in segments:
            role = self.speaker_role_map.get(seg.speaker, MedicalRole.UNKNOWN)
            seg.role = role
            seg.speaker_label = f"{role.value} ({seg.speaker})"

        return segments

    def _infer_roles(self, segments: list) -> None:
        """Infer speaker roles using heuristics on the full transcript.

        Strategy:
        1. Keyword scoring: count doctor/patient keywords per speaker.
        2. Speaking time: assign DOCTOR to the speaker with more total speech
           if keyword scores are tied.

        Args:
            segments: List of AlignedSegment.
        """
        speaker_stats: Dict[str, Dict] = {}

        for seg in segments:
            sp = seg.speaker
            if sp not in speaker_stats:
                speaker_stats[sp] = {
                    "doctor_score": 0,
                    "patient_score": 0,
                    "duration": 0.0,
                    "text": "",
                }
            speaker_stats[sp]["duration"] += seg.duration
            speaker_stats[sp]["text"] += " " + seg.text.lower()

        for sp, stats in speaker_stats.items():
            text = stats["text"]
            stats["doctor_score"] = sum(kw in text for kw in DOCTOR_KEYWORDS)
            stats["patient_score"] = sum(kw in text for kw in PATIENT_KEYWORDS)

        speakers = list(speaker_stats.keys())

        if len(speakers) == 0:
            return
        elif len(speakers) == 1:
            self.speaker_role_map[speakers[0]] = MedicalRole.DOCTOR
            return

        # Assign DOCTOR to the speaker with higher doctor_score
        # Tiebreak: DOCTOR speaks more (more total duration)
        def doctor_score(sp: str) -> tuple:
            stats = speaker_stats[sp]
            return (
                stats["doctor_score"] - stats["patient_score"],
                stats["duration"],
            )

        sorted_speakers = sorted(speakers, key=doctor_score, reverse=True)
        self.speaker_role_map[sorted_speakers[0]] = MedicalRole.DOCTOR

        # Assign PATIENT to remaining speakers
        for sp in sorted_speakers[1:]:
            self.speaker_role_map[sp] = MedicalRole.PATIENT

        logger.info(
            "Inferred roles: %s",
            {sp: role.value for sp, role in self.speaker_role_map.items()},
        )

    def set_role(self, speaker: str, role: MedicalRole) -> None:
        """Manually set the role for a speaker (e.g., from user input).

        Args:
            speaker: Speaker identifier.
            role: MedicalRole to assign.
        """
        self.speaker_role_map[speaker] = role
        logger.info("Role set: %s → %s", speaker, role.value)

    def get_role(self, speaker: str) -> MedicalRole:
        """Get the role for a speaker.

        Args:
            speaker: Speaker identifier.

        Returns:
            MedicalRole or UNKNOWN if not mapped.
        """
        return self.speaker_role_map.get(speaker, MedicalRole.UNKNOWN)
