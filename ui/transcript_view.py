"""Transcript visualization component for Streamlit UI."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from typing import List, Any

import streamlit as st

from postprocessing.role_labeling import MedicalRole
from utils.timestamp_utils import seconds_to_hms


# Color mapping for roles
ROLE_COLORS = {
    MedicalRole.DOCTOR: "#1a73e8",    # Blue for doctor
    MedicalRole.PATIENT: "#34a853",   # Green for patient
    MedicalRole.UNKNOWN: "#9e9e9e",   # Grey for unknown
}

ROLE_ICONS = {
    MedicalRole.DOCTOR: "👨‍⚕️",
    MedicalRole.PATIENT: "🧑",
    MedicalRole.UNKNOWN: "❓",
}


def render_transcript_segment(segment: Any) -> None:
    """Render a single transcript segment with role-based styling.

    Args:
        segment: AlignedSegment with .speaker, .text, .start, .end, .role attributes.
    """
    role = getattr(segment, "role", MedicalRole.UNKNOWN)
    color = ROLE_COLORS.get(role, ROLE_COLORS[MedicalRole.UNKNOWN])
    icon = ROLE_ICONS.get(role, "❓")
    timestamp = seconds_to_hms(segment.start)
    role_label = role.value if isinstance(role, MedicalRole) else str(role)

    html = f"""
    <div class="transcript-segment" style="border-left: 4px solid {color}; padding: 8px 12px; margin: 6px 0; border-radius: 4px; background: #f8f9fa;">
        <div class="segment-header" style="color: {color}; font-weight: bold; margin-bottom: 4px;">
            {icon} {role_label}
            <span class="timestamp" style="color: #888; font-size: 0.85em; font-weight: normal; margin-left: 12px;">{timestamp}</span>
        </div>
        <div class="segment-text" style="color: #212529; font-family: 'Georgia', serif; font-size: 1.0em; line-height: 1.5;">
            {segment.text}
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_full_transcript(segments: List[Any]) -> None:
    """Render the complete transcript with all segments.

    Groups consecutive segments from the same speaker.

    Args:
        segments: List of AlignedSegment objects.
    """
    if not segments:
        st.info("Transcriptul este gol.")
        return

    for seg in segments:
        render_transcript_segment(seg)


def render_transcript_summary(segments: List[Any]) -> None:
    """Render statistics about the transcript.

    Args:
        segments: List of AlignedSegment objects.
    """
    if not segments:
        return

    from collections import defaultdict

    stats = defaultdict(lambda: {"count": 0, "duration": 0.0, "words": 0})
    for seg in segments:
        role = getattr(seg, "role", MedicalRole.UNKNOWN)
        key = role.value if isinstance(role, MedicalRole) else str(role)
        stats[key]["count"] += 1
        stats[key]["duration"] += seg.duration
        stats[key]["words"] += len(seg.text.split())

    st.subheader("📊 Statistici Consultație")
    cols = st.columns(len(stats))
    for col, (role_name, data) in zip(cols, stats.items()):
        with col:
            st.metric(
                label=role_name,
                value=f"{int(data['duration'])}s",
                delta=f"{data['words']} cuvinte",
            )
