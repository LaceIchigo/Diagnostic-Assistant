"""Streamlit application for real-time medical consultation transcription."""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import time
from threading import Thread
from typing import List, Optional

import numpy as np
import streamlit as st

from audio.capture import AudioCapture
from pipeline.orchestrator import PipelineConfig, PipelineOrchestrator, PipelineOutput
from pipeline.streaming import StreamingPipeline
from postprocessing.role_labeling import MedicalRole
from ui.transcript_view import render_transcript_segment, render_full_transcript
from utils.logger import setup_logger

setup_logger(level="INFO")

# Page configuration
st.set_page_config(
    page_title="Diagnostic Assistant",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load custom CSS
css_path = os.path.join(os.path.dirname(__file__), "static", "style.css")
if os.path.exists(css_path):
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def init_session_state() -> None:
    """Initialize Streamlit session state variables."""
    if "recording" not in st.session_state:
        st.session_state.recording = False
    if "transcript" not in st.session_state:
        st.session_state.transcript = []
    if "pipeline" not in st.session_state:
        st.session_state.pipeline = None
    if "capture" not in st.session_state:
        st.session_state.capture = None


def create_pipeline(
    model_size: str,
    language: str,
    device_index: int,
    vad_threshold: float,
) -> StreamingPipeline:
    """Create and configure a StreamingPipeline instance.

    Args:
        model_size: Whisper model size.
        language: Language code.
        device_index: Audio device index.
        vad_threshold: VAD speech probability threshold.

    Returns:
        Configured StreamingPipeline.
    """
    config = PipelineConfig(
        model_size=model_size,
        language=language,
        vad_threshold=vad_threshold,
    )

    def on_output(output: PipelineOutput) -> None:
        st.session_state.transcript.extend(output.segments)

    return StreamingPipeline(config=config, on_output=on_output)


def render_sidebar() -> dict:
    """Render sidebar configuration controls and return settings dict."""
    st.sidebar.title("⚙️ Configurare")

    st.sidebar.subheader("Model ASR")
    model_size = st.sidebar.selectbox(
        "Dimensiune model Whisper",
        options=["tiny", "base", "small", "medium", "large-v2"],
        index=3,  # medium
        help="Modele mai mari = mai accurate, dar mai lente",
    )

    language = st.sidebar.selectbox(
        "Limbă",
        options=["ro", "en", "de", "fr"],
        index=0,
        help="Limba principală a consultației",
    )

    st.sidebar.subheader("Audio")
    try:
        devices = AudioCapture.list_devices()
        device_names = [f"{d['index']}: {d['name']}" for d in devices]
        device_idx = st.sidebar.selectbox(
            "Dispozitiv audio",
            options=range(len(device_names)),
            format_func=lambda i: device_names[i],
        )
        selected_device = devices[device_idx]["index"] if devices else 0
    except Exception:
        selected_device = 0
        st.sidebar.info("Folosind dispozitivul audio implicit.")

    vad_threshold = st.sidebar.slider(
        "Prag VAD (sensibilitate voce)",
        min_value=0.1,
        max_value=0.9,
        value=0.5,
        step=0.05,
        help="Valori mai mari = mai puține false pozitive (dar pot pierde vorbire slabă)",
    )

    st.sidebar.subheader("Roluri")
    doctor_speaker = st.sidebar.selectbox(
        "Vorbitor doctor",
        options=["Auto-detectare", "SPEAKER_00", "SPEAKER_01"],
        help="Dacă cunoașteți ID-ul vorbitorului doctor, selectați-l explicit",
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("### ℹ️ Despre")
    st.sidebar.markdown(
        "Diagnostic Assistant — sistem de transcriere în timp real pentru consultații medicale.\n\n"
        "⚠️ **Decizia medicală finală aparține exclusiv medicului.**"
    )

    return {
        "model_size": model_size,
        "language": language,
        "device_index": selected_device,
        "vad_threshold": vad_threshold,
        "doctor_speaker": doctor_speaker,
    }


def main() -> None:
    """Main Streamlit application."""
    init_session_state()
    settings = render_sidebar()

    # Header
    st.title("🩺 Diagnostic Assistant")
    st.markdown("**Transcriere în timp real a consultațiilor medicale**")

    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        if not st.session_state.recording:
            if st.button("▶️ Pornire înregistrare", use_container_width=True, type="primary"):
                st.session_state.recording = True
                st.session_state.transcript = []

                pipeline = create_pipeline(
                    model_size=settings["model_size"],
                    language=settings["language"],
                    device_index=settings["device_index"],
                    vad_threshold=settings["vad_threshold"],
                )
                st.session_state.pipeline = pipeline
                pipeline.start()
                st.rerun()
        else:
            if st.button("⏹️ Oprire înregistrare", use_container_width=True, type="secondary"):
                st.session_state.recording = False
                if st.session_state.pipeline:
                    st.session_state.pipeline.stop()
                    st.session_state.pipeline = None
                st.rerun()

    with col2:
        if st.button("🗑️ Șterge transcript", use_container_width=True):
            st.session_state.transcript = []
            st.rerun()

    with col3:
        if st.session_state.recording:
            st.markdown("🔴 **Live**")
        else:
            st.markdown("⚫ **Oprit**")

    # Status bar
    st.markdown("---")

    if st.session_state.recording:
        st.info(
            "🎙️ Înregistrare activă — vorbitorii sunt detectați automat. "
            "Apăsați '⏹️ Oprire înregistrare' pentru a finaliza."
        )

    # Transcript display
    st.subheader("📝 Transcript")

    if not st.session_state.transcript:
        st.markdown(
            "_Transcriptul va apărea aici în timp real după pornirea înregistrării..._"
        )
    else:
        transcript_container = st.container()
        with transcript_container:
            render_full_transcript(st.session_state.transcript)

    # Auto-refresh when recording
    if st.session_state.recording:
        # Feed audio to pipeline from capture
        if st.session_state.pipeline and st.session_state.capture:
            capture: AudioCapture = st.session_state.capture
            chunk = capture.read_chunk(timeout=0.1)
            if chunk is not None and st.session_state.pipeline:
                st.session_state.pipeline.push_audio(chunk)

        time.sleep(1.0)
        st.rerun()


if __name__ == "__main__":
    main()
