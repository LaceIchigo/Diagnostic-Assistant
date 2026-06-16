"""
Fuzionează adaptorul LoRA antrenat prin FL în modelul de bază Llama-3.2-3B-Instruct.
Rezultatul (model complet fp16, safetensors) poate fi importat direct în Ollama.

Rulare:
    huggingface-cli login        # o singura data, cu tokenul tau HF (modelul Meta e gated)
    python merge_adapter.py
"""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

BASE    = "meta-llama/Llama-3.2-3B-Instruct"
ADAPTER = r"D:\Angular\Diagnostic-Assistant\adapter"
OUT     = r"D:\Angular\Diagnostic-Assistant\llama32-medical-merged"

print("[1/4] Incarc modelul de baza in fp16 (pe CPU)...")
model = AutoModelForCausalLM.from_pretrained(BASE, torch_dtype=torch.float16)

print("[2/4] Aplic adaptorul LoRA...")
model = PeftModel.from_pretrained(model, ADAPTER)

print("[3/4] Fuzionez adaptorul in greutatile de baza (merge_and_unload)...")
model = model.merge_and_unload()

print("[4/4] Salvez modelul fuzionat + tokenizer...")
model.save_pretrained(OUT, safe_serialization=True)
AutoTokenizer.from_pretrained(BASE).save_pretrained(OUT)

print("Gata. Model fuzionat salvat in:", OUT)
