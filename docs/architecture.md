# Arhitectura Sistemului Diagnostic Assistant

## Prezentare Generală

Diagnostic Assistant implementează un pipeline în timp real de 10 pași pentru transcrierea și analiza consultațiilor medicale audio.

## Diagrama Pipeline-ului Principal

```mermaid
flowchart TD
    A[🎤 Microfon / Intrare Audio] --> B[Buffer Circular Thread-Safe]
    B --> C[Chunking 1-2s cu Overlap]
    C --> D{VAD\nSilero VAD}
    D -->|Speech detectat| E[ASR\nWhisper medium]
    D -->|Silențiu| C
    E --> F[Timestamps cuvânt/segment]
    F --> G[Diarizare\npyannote.audio]
    G --> H[Aliniere\nDiarizare ↔ ASR]
    H --> I[Punctuație\ndeepmlpunct]
    I --> J[Etichetare Roluri\nDoctor / Pacient]
    J --> K[UI Streamlit\nTranscript Live]
    J --> L[Output JSON/TXT]
    K --> M[Evaluare\nWER / DER]
```

## Diagrama Componentelor

```mermaid
graph TB
    subgraph audio_layer["Strat Audio (src/audio/)"]
        CAP[capture.py\nAudioCapture]
        CHK[chunking.py\nAudioChunker]
        PRE[preprocessing.py\nAudioPreprocessor]
    end

    subgraph ai_layer["Strat AI (src/vad/, src/asr/, src/diarization/)"]
        VAD[silero_vad.py\nSileroVAD]
        ASR[whisper_asr.py\nWhisperASR]
        DIAR[pyannote_diar.py\nPyannoteDiarizer]
        ALIGN[alignment.py\nDiarizationAligner]
    end

    subgraph post_layer["Post-procesare (src/postprocessing/)"]
        PUNCT[punctuation.py\nPunctuationProcessor]
        ROLE[role_labeling.py\nRoleLabeler]
    end

    subgraph pipeline_layer["Pipeline (src/pipeline/)"]
        ORCH[orchestrator.py\nPipelineOrchestrator]
        STREAM[streaming.py\nStreamingPipeline]
    end

    subgraph utils_layer["Utilitare (src/utils/)"]
        BUF[circular_buffer.py\nCircularBuffer]
        TS[timestamp_utils.py]
        LOG[logger.py]
    end

    subgraph ui_layer["UI (ui/)"]
        APP[app.py\nStreamlit App]
        TV[transcript_view.py]
    end

    CAP --> BUF --> CHK --> PRE --> VAD --> ASR
    ASR --> ALIGN
    DIAR --> ALIGN
    ALIGN --> PUNCT --> ROLE
    ROLE --> ORCH --> APP
    ORCH --> STREAM
```

## Diagrama Fluxului de Date

```mermaid
sequenceDiagram
    participant Mic as Microfon
    participant Buf as Buffer Circular
    participant VAD as Silero VAD
    participant ASR as Whisper ASR
    participant Diar as Pyannote Diarizer
    participant Align as Aligner
    participant Post as Post-procesare
    participant UI as Streamlit UI

    Mic->>Buf: audio_chunk (numpy array, 16kHz)
    Buf->>VAD: chunk + context
    VAD-->>ASR: speech_segments [{start, end}]
    ASR-->>Align: transcribed_words [{word, start, end, confidence}]
    Diar-->>Align: speaker_turns [{speaker, start, end}]
    Align-->>Post: aligned_segments [{speaker, text, start, end}]
    Post-->>UI: structured_transcript [{role, text, timestamp}]
```

## Arhitectura Buffer-ului Circular

```mermaid
graph LR
    subgraph buffer["CircularBuffer (Thread-Safe)"]
        direction LR
        W[Write Thread\nAudioCapture] -->|put| Q[(Queue\ncapacity=N)]
        Q -->|get| R[Read Thread\nPipeline]
    end
```

## Scalabilitate

Arhitectura suportă 2–200 cabinete fără modificări:

```mermaid
graph TB
    subgraph cabinets["Cabinete Medicale"]
        C1[Cabinet 1\nDevice Index 0]
        C2[Cabinet 2\nDevice Index 1]
        Cn[Cabinet N\nDevice Index N]
    end
    subgraph pipelines["Pipeline Instanțe"]
        P1[Pipeline 1\nconfig_1.yaml]
        P2[Pipeline 2\nconfig_2.yaml]
        Pn[Pipeline N\nconfig_n.yaml]
    end
    C1 --> P1
    C2 --> P2
    Cn --> Pn
    P1 & P2 & Pn --> AGG[Agregator\nOutput central]
```

## Detalii Tehnice

### Fereastra Sliding pentru Diarizare
- Fereastră: 20 secunde
- Pas: 10 secunde (50% overlap)
- Asigură continuitate în identificarea vorbitorului

### Alinierea Timestamp-urilor
- ASR produce timestamps la nivel de cuvânt
- Diarizarea produce intervale per vorbitor
- Alinierea folosește intersecția intervalelor (overlap maxim)

### Thread Safety
- `CircularBuffer` folosește `threading.Lock` și `queue.Queue`
- Producătorul (AudioCapture) și consumatorul (Pipeline) rulează în thread-uri separate
