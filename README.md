# Diagnostic Assistant — Sistem de Transcriere în Timp Real a Consultațiilor Medicale

## Descriere

**Diagnostic Assistant** este un sistem avansat de transcriere automată a consultațiilor medicale în timp real, utilizând tehnologii de ultimă generație pentru recunoașterea vorbirii (ASR), diarizarea vorbitorului și etichetarea rolurilor (Doctor/Pacient). Sistemul oferă suport decizional medicilor prin standardizarea și structurarea informației audio în text structurat.

Proiectul rulează pe **AMD GPU cu ROCm** (fără dependențe NVIDIA/CUDA), asigurând compatibilitate largă cu echipamentele medicale actuale.

## Arhitectura Sistemului

Sistemul implementează un pipeline de 10 pași:

```
Microfon → Buffer Circular → VAD → ASR (Whisper) → Diarizare (pyannote)
       → Aliniere → Punctuație → Etichetare Roluri → UI (Streamlit)
                                                    ↓
                                           Evaluare WER/DER
```

### Componente Principale

| Pas | Componentă | Tehnologie |
|-----|-----------|-----------|
| 1 | Captură Audio | sounddevice + buffer circular |
| 2 | Chunking | Ferestre 1–2s cu overlap |
| 3 | VAD | Silero VAD (PyTorch/ROCm) |
| 4 | ASR | faster-whisper / openai-whisper |
| 5 | Diarizare | pyannote.audio 3.x |
| 6 | Aliniere | Potrivire timestamp-uri |
| 7 | Punctuație | deepmultilingualpunctuation |
| 8 | Etichetare Roluri | Heuristici + classifier opțional |
| 9 | Interfață | Streamlit |
| 10 | Evaluare | jiwer (WER), pyannote.metrics (DER) |

## Instalare cu AMD ROCm

### Cerințe de sistem
- Linux (Ubuntu 20.04/22.04 recomandat)
- AMD GPU cu suport ROCm (RX 6000/7000 series, Instinct MI series)
- ROCm 5.6+ instalat
- Python 3.9+

### Instalare ROCm

```bash
# Descarcă și rulează scriptul de instalare
chmod +x scripts/install_rocm.sh
./scripts/install_rocm.sh
```

Sau manual:

```bash
# Ubuntu 22.04
wget https://repo.radeon.com/amdgpu-install/6.0.2/ubuntu/jammy/amdgpu-install_6.0.2.60002-1_all.deb
sudo apt install ./amdgpu-install_6.0.2.60002-1_all.deb
sudo amdgpu-install -y --usecase=rocm

# Adaugă utilizatorul la grupurile necesare
sudo usermod -a -G render,video $LOGNAME

# Verifică instalarea
rocminfo
```

### Instalare PyTorch cu ROCm

```bash
# PyTorch pentru ROCm 6.0
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.0
```

### Instalare dependențe proiect

```bash
# Clonează repository
git clone https://github.com/LaceIchigo/Diagnostic-Assistant.git
cd Diagnostic-Assistant

# Creează mediu virtual
python -m venv venv
source venv/bin/activate

# Instalează dependențe
pip install -r requirements.txt

# Instalează pachetul
pip install -e .
```

### Configurare variabile de mediu

```bash
cp .env.example .env
# Editează .env și setează variabilele necesare (HUGGINGFACE_TOKEN, etc.)
```

## Utilizare

### Pornire UI Streamlit

```bash
streamlit run ui/app.py
```

### Rulare Pipeline din linie de comandă

```bash
python scripts/run_pipeline.py --config config/default.yaml --device-index 0
```

### Rulare cu parametri personalizați

```bash
python scripts/run_pipeline.py \
  --model-size medium \
  --language ro \
  --output-dir ./output \
  --device-index 0
```

## Evaluare

### Rulare suite de evaluare WER/DER

```bash
python scripts/run_evaluation.py --test-dir evaluation/datasets/ --output results/
```

### Rulare teste unitare

```bash
pytest tests/ -v
```

### Generare raport automat

```bash
python scripts/generate_report.py --results-dir results/ --output report.html
```

## Structura Proiectului

```
Diagnostic-Assistant/
├── config/          # Configurări YAML
├── docs/            # Documentație detaliată
├── src/             # Cod sursă principal
│   ├── audio/       # Captură și procesare audio
│   ├── vad/         # Voice Activity Detection
│   ├── asr/         # Recunoaștere automată a vorbirii
│   ├── diarization/ # Diarizare vorbitori
│   ├── postprocessing/ # Punctuație și etichetare roluri
│   ├── pipeline/    # Orchestrare pipeline
│   └── utils/       # Utilitare comune
├── ui/              # Interfață Streamlit
├── evaluation/      # Evaluare WER/DER
├── scripts/         # Script-uri de rulare
└── tests/           # Teste unitare și E2E
```

## Considerații Etice

Sistemul **Diagnostic Assistant** a fost conceput cu respectarea strictă a principiilor etice medicale și de confidențialitate a datelor:

- **Confidențialitate**: Modelul nu are acces la date personale identificabile. Toate datele audio sunt procesate local, fără transmitere în cloud.
- **Abstractizare**: Învățarea se face exclusiv pe date abstractizate, fără asociere cu identitățile pacienților.
- **Responsabilitate medicală**: Decizia medicală finală aparține exclusiv medicului. Sistemul oferă doar suport și nu poate înlocui judecata clinică.
- **Rol suport**: Sistemul are rol de suport și standardizare a informației, nu de diagnostic automat.
- **GDPR**: Conformitate cu Regulamentul General privind Protecția Datelor (GDPR) și legislația națională.
- **Transparență**: Utilizatorii sunt informați că consultația este transcrisă automat.

Pentru detalii complete, consultați [docs/ethical_guidelines.md](docs/ethical_guidelines.md).

## Scalabilitate

Arhitectura sistemului suportă scalare de la 2 cabinete medicale la 200+ fără modificări arhitecturale, prin:
- Configurare per-cabinet prin fișiere YAML
- Pipeline stateless cu state management extern
- Suport multi-device audio
- Buffer circular thread-safe

## Licență

MIT License — vezi [LICENSE](LICENSE) pentru detalii.

## Contribuții

Contribuțiile sunt binevenite! Consultați [CONTRIBUTING.md](CONTRIBUTING.md) sau deschideți un issue.
