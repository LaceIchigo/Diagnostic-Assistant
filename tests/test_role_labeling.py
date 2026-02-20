"""Tests for role labeling module."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

from postprocessing.role_labeling import MedicalRole, RoleLabeler
from diarization.alignment import AlignedSegment


def make_segment(speaker, text, start=0.0, end=5.0):
    return AlignedSegment(speaker=speaker, text=text, start=start, end=end)


class TestMedicalRole:
    def test_values(self):
        assert MedicalRole.DOCTOR.value == "Doctor"
        assert MedicalRole.PATIENT.value == "Pacient"
        assert MedicalRole.UNKNOWN.value == "Necunoscut"


class TestRoleLabeler:
    def test_explicit_mapping(self):
        labeler = RoleLabeler(
            speaker_role_map={
                "SPEAKER_00": MedicalRole.DOCTOR,
                "SPEAKER_01": MedicalRole.PATIENT,
            }
        )
        segments = [
            make_segment("SPEAKER_00", "Cum vă simțiți?"),
            make_segment("SPEAKER_01", "Mă doare capul."),
        ]
        result = labeler.label_segments(segments)

        assert result[0].role == MedicalRole.DOCTOR
        assert result[1].role == MedicalRole.PATIENT

    def test_doctor_speaker_kwarg(self):
        labeler = RoleLabeler(doctor_speaker="SPEAKER_00")
        assert labeler.speaker_role_map["SPEAKER_00"] == MedicalRole.DOCTOR

    def test_infer_roles_doctor_keywords(self):
        """Doctor uses medical keywords, patient describes symptoms."""
        labeler = RoleLabeler()
        segments = [
            make_segment(
                "SPEAKER_00",
                "Prescriu tratament și recomand analize pentru diagnostic",
                start=0.0, end=10.0
            ),
            make_segment(
                "SPEAKER_01",
                "Mă doare și simt greață",
                start=11.0, end=15.0
            ),
        ]
        labeler.label_segments(segments)

        # After inference, SPEAKER_00 should be doctor (more doctor keywords)
        assert labeler.get_role("SPEAKER_00") == MedicalRole.DOCTOR
        assert labeler.get_role("SPEAKER_01") == MedicalRole.PATIENT

    def test_infer_roles_single_speaker(self):
        """Single speaker defaults to DOCTOR."""
        labeler = RoleLabeler()
        segments = [make_segment("SPEAKER_00", "Bună ziua", start=0.0, end=5.0)]
        labeler.label_segments(segments)
        assert labeler.get_role("SPEAKER_00") == MedicalRole.DOCTOR

    def test_get_role_unknown(self):
        labeler = RoleLabeler()
        role = labeler.get_role("SPEAKER_99")
        assert role == MedicalRole.UNKNOWN

    def test_set_role(self):
        labeler = RoleLabeler()
        labeler.set_role("SPEAKER_00", MedicalRole.PATIENT)
        assert labeler.get_role("SPEAKER_00") == MedicalRole.PATIENT

    def test_label_segments_adds_role_attribute(self):
        labeler = RoleLabeler(
            speaker_role_map={"SPEAKER_00": MedicalRole.DOCTOR}
        )
        seg = make_segment("SPEAKER_00", "Test")
        labeler.label_segments([seg])
        assert hasattr(seg, "role")
        assert seg.role == MedicalRole.DOCTOR

    def test_label_segments_adds_speaker_label_attribute(self):
        labeler = RoleLabeler(
            speaker_role_map={"SPEAKER_00": MedicalRole.DOCTOR}
        )
        seg = make_segment("SPEAKER_00", "Test")
        labeler.label_segments([seg])
        assert hasattr(seg, "speaker_label")
        assert "Doctor" in seg.speaker_label
