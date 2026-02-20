# Structura Capitolelor Lucrării de Licență

## Titlu Propus
**„Sistem de Transcriere în Timp Real a Consultațiilor Medicale cu Diarizare și Etichetare Automată a Rolurilor"**

---

## Capitolul 1: Introducere

### 1.1 Motivație și Context
- Necesitatea documentării eficiente a consultațiilor medicale
- Problemele documentării manuale: timp, erori, incompletitudine
- Potențialul inteligenței artificiale în asistarea medicilor

### 1.2 Obiectivele Lucrării
- Obiectivul principal: sistem de transcriere în timp real
- Obiective secundare: diarizare, etichetare roluri, suport decizional
- Constrângeri: compatibilitate AMD/ROCm, limba română, GDPR

### 1.3 Contribuții
- Pipeline integrat ASR + Diarizare pentru română
- Adaptare pentru AMD GPU cu ROCm
- Evaluare pe scenarii medicale reale

### 1.4 Structura Lucrării
- Prezentare sumară a capitolelor

---

## Capitolul 2: Stadiul Artei (State of the Art)

### 2.1 Recunoașterea Automată a Vorbirii (ASR)
- Evoluție: GMM-HMM → DNN → Transformer
- Modele actuale: Whisper (OpenAI), wav2vec 2.0, HuBERT
- Performanță pe limba română

### 2.2 Diarizarea Vorbitorului
- Paradigme: EEND, clustering-based
- pyannote.audio: arhitectură și performanță
- DER pe benchmark-uri publice

### 2.3 Procesare Audio în Timp Real
- VAD (Voice Activity Detection): algoritmi și soluții
- Silero VAD: avantaje PyTorch-native
- Latență vs. acuratețe

### 2.4 NLP pentru Text Medical
- Punctuație și capitalizare automată
- Etichetare entități medicale (NER)
- Modele multilinguale

### 2.5 Sisteme Similare
- Dragon Medical (Nuance)
- Amazon Transcribe Medical
- Soluții open-source existente
- Limitări și gap-uri identificate

---

## Capitolul 3: Fundamentele Teoretice

### 3.1 Procesarea Semnalelor Audio
- Reprezentare numerică a sunetului
- Frecvența de eșantionare, adâncimea de bit
- STFT, Mel-spectrogramă, MFCC

### 3.2 Rețele Neuronale pentru Audio
- Transformeri (Attention mechanism)
- Arhitectura Whisper (encoder-decoder)
- Pyannote: segmentare + clustering

### 3.3 Metrici de Evaluare
- WER (Word Error Rate): formulă și interpretare
- DER (Diarization Error Rate): componente
- Limitări și alternative (MER, CER)

### 3.4 Compatibilitate AMD ROCm
- ROCm vs. CUDA: diferențe arhitecturale
- HIP: portabilitate cod GPU
- PyTorch pe ROCm: configurare și optimizare

---

## Capitolul 4: Proiectarea Sistemului

### 4.1 Cerințe Funcționale și Non-funcționale
- Cerințe funcționale: transcriere, diarizare, UI
- Cerințe non-funcționale: latență, acuratețe, scalabilitate
- Constrângeri: GDPR, compatibilitate hardware

### 4.2 Arhitectura Pipeline-ului
- Prezentare generală: 10 pași
- Diagrame arhitecturale (Mermaid)
- Justificarea alegerii componentelor

### 4.3 Proiectarea Modulelor
- Modul Audio: captură, chunking, preprocesare
- Modul VAD: Silero VAD, parametrizare
- Modul ASR: Whisper, configurare pentru română
- Modul Diarizare: pyannote.audio, fereastră sliding
- Modul Post-procesare: punctuație, etichetare roluri

### 4.4 Proiectarea Interfeței Utilizator
- Principii UX pentru aplicații medicale
- Mockup-uri Streamlit
- Vizualizare transcript pe roluri

### 4.5 Considerații de Scalabilitate
- Model multi-cabinet
- State management
- Configurare flexibilă

---

## Capitolul 5: Implementare

### 5.1 Mediul de Dezvoltare
- Hardware: specificații GPU AMD
- Instalare ROCm + PyTorch
- Structura proiectului Python

### 5.2 Implementarea Capturii Audio
- sounddevice: callback-based capture
- Buffer circular thread-safe
- Chunking cu overlap

### 5.3 Implementarea VAD
- Încărcare Silero VAD via torch.hub
- Procesare în timp real
- Filtrare segmente de vorbire

### 5.4 Implementarea ASR
- Inițializare faster-whisper
- Transcriere cu timestamps la nivel de cuvânt
- Optimizări pentru română

### 5.5 Implementarea Diarizării
- Pipeline pyannote.audio
- Fereastră sliding
- Gestionare stare între ferestre

### 5.6 Alinierea Diarizare-ASR
- Algoritm de aliniere timestamp
- Gestionare cazuri marginale (suprapuneri)

### 5.7 Post-procesare
- Punctuație: deepmultilingualpunctuation
- Etichetare roluri: heuristici + classifier

### 5.8 Interfața Streamlit
- Componente UI
- Actualizare transcript în timp real
- Color-coding pe roluri

---

## Capitolul 6: Evaluare și Rezultate

### 6.1 Metodologia de Evaluare
- Setul de date de test
- Protocol de evaluare
- Instrumente utilizate

### 6.2 Evaluarea ASR (WER)
- Rezultate pe scenarii
- Analiza erorilor frecvente
- Comparație model sizes

### 6.3 Evaluarea Diarizării (DER)
- Rezultate pe scenarii
- Analiza confuziilor de vorbitor
- Impact număr vorbitori

### 6.4 Evaluarea End-to-End
- Latență pipeline complet
- Utilizare resurse GPU/CPU
- Performanță pe termen lung (30 min)

### 6.5 Discuție Rezultate
- Comparație cu obiectivele inițiale
- Limitări identificate
- Sugestii de îmbunătățire

---

## Capitolul 7: Considerații Etice și Juridice

### 7.1 GDPR și Confidențialitatea Datelor
- Principii aplicabile
- Implementare tehnică GDPR

### 7.2 Responsabilitatea Sistemelor AI în Medicină
- Limitele sistemului
- Rolul medicului vs. sistemului

### 7.3 Transparență și Explicabilitate
- Ce poate/nu poate face sistemul
- Comunicare cu pacienții

### 7.4 Biasuri și Echitate
- Potențiale biasuri în date
- Performanță egală indiferent de vorbitor

---

## Capitolul 8: Concluzii și Lucrări Viitoare

### 8.1 Concluzii
- Rezumat contribuții
- Atingerea obiectivelor
- Impactul potențial

### 8.2 Lucrări Viitoare
- Fine-tuning Whisper pe date medicale românești
- Extindere la mai mult de 2 vorbitori
- Integrare cu sisteme EMR
- Aplicație mobilă
- Suport dialecte și accente

---

## Bibliografie

- Radford et al. (2023) — Robust Speech Recognition via Large-Scale Weak Supervision (Whisper)
- Bredin et al. (2023) — pyannote.audio 2.1
- Silero Team (2021) — Silero VAD
- Guhr et al. (2021) — FullStop: Multilingual Deep Models for Punctuation Prediction
- Park et al. (2022) — A Review of Speaker Diarization

---

## Anexe

### Anexa A: Instrucțiuni de Instalare
### Anexa B: Manual de Utilizare
### Anexa C: Cod sursă selectat
### Anexa D: Rezultate evaluare complete
### Anexa E: Acorduri etice și consimțăminte
