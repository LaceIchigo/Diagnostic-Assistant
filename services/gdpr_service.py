"""
services/gdpr_service.py — Criptare date medicale si GDPR compliance.
"""
import os
import hashlib
import re
import json
from datetime import datetime
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()


class GDPRManager:
    def __init__(self):
        self._init_encryption_key()
        self._init_audit_log()

    # ── Criptare AES-256 ────────────────────────────────────────────────────

    def _init_encryption_key(self):
        key = os.getenv("ENCRYPTION_KEY")
        if not key:
            key = Fernet.generate_key().decode()
            print("=" * 60)
            print("ATENTIE: Cheie de criptare noua generata!")
            print(f"Adauga in .env: ENCRYPTION_KEY={key}")
            print("IMPORTANT: Fara aceasta cheie datele criptate nu pot fi recuperate!")
            print("=" * 60)
        self.fernet = Fernet(key.encode() if isinstance(key, str) else key)

    def encrypt(self, text: str) -> str:
        if not text:
            return ""
        return self.fernet.encrypt(text.encode("utf-8")).decode("utf-8")

    def decrypt(self, encrypted_text: str) -> str:
        if not encrypted_text:
            return ""
        try:
            return self.fernet.decrypt(encrypted_text.encode("utf-8")).decode("utf-8")
        except Exception:
            return encrypted_text  # date vechi necriptate

    # ── Hashing CNP ─────────────────────────────────────────────────────────

    def hash_cnp(self, cnp: str) -> str:
        salt = os.getenv("CNP_SALT", "medical_ai_default_salt_change_me")
        return hashlib.sha256(f"{salt}:{cnp}".encode()).hexdigest()

    def verify_cnp(self, cnp_input: str, cnp_hash: str) -> bool:
        return self.hash_cnp(cnp_input) == cnp_hash

    def mask_cnp(self, cnp: str) -> str:
        if not cnp or len(cnp) < 6:
            return "***"
        return cnp[:3] + "*" * (len(cnp) - 5) + cnp[-2:]

    # ── Anonimizare text pentru Federated Learning ──────────────────────────

    def anonimizeaza_text(self, text: str) -> str:
        if not text:
            return ""
        result = text
        result = re.sub(r"\b[1-8]\d{12}\b", "[CNP_REDACTED]", result)
        result = re.sub(r"\b(0[237]\d{8}|\+40\d{9}|07\d{8})\b", "[PHONE_REDACTED]", result)
        result = re.sub(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "[EMAIL_REDACTED]", result,
        )
        prenume_comune = [
            "Ion", "Maria", "Alexandru", "Elena", "Andrei", "Ana",
            "Mihai", "Ioana", "Cristian", "Adriana", "Gheorghe",
            "Popescu", "Ionescu", "Popa", "Constantin", "Stan",
            "Dumitrescu", "Stoica", "Munteanu", "Radu", "Moldovan",
        ]
        for nume in prenume_comune:
            result = re.sub(rf"\b{nume}\b", "[NAME_REDACTED]", result, flags=re.IGNORECASE)
        return result

    # ── Audit log — GDPR Art. 30 ────────────────────────────────────────────

    def _init_audit_log(self):
        self.audit_file = os.getenv("AUDIT_LOG_FILE", "audit_gdpr.log")

    def log_access(self, action: str, user: str, details: str = ""):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "user": user,
            "details": details,
        }
        try:
            with open(self.audit_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"Eroare audit log: {e}")

    def get_audit_log(self, limit: int = 50) -> list:
        try:
            with open(self.audit_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            return list(reversed([json.loads(line) for line in lines[-limit:]]))
        except FileNotFoundError:
            return []

    # ── GDPR Art. 17 — Dreptul la stergere ─────────────────────────────────

    def sterge_date_pacient(self, db, pacient_id: int, user: str = "system") -> dict:
        from models.database import Pacient, Consultatie

        pacient = db.query(Pacient).filter(Pacient.id == pacient_id).first()
        if not pacient:
            return {"success": False, "message": "Pacientul nu exista."}

        consultatii_count = (
            db.query(Consultatie).filter(Consultatie.pacient_id == pacient_id).count()
        )
        db.query(Consultatie).filter(Consultatie.pacient_id == pacient_id).delete()
        db.delete(pacient)
        db.commit()

        self.log_access(
            action="RIGHT_TO_ERASURE",
            user=user,
            details=f"Pacient ID {pacient_id} sters cu {consultatii_count} consultatii",
        )
        return {
            "success": True,
            "message": f"Date sterse: 1 pacient + {consultatii_count} consultatii.",
            "consultatii_sterse": consultatii_count,
        }

    # ── GDPR Art. 15 + 20 — Export date pacient ─────────────────────────────

    def export_date_pacient(self, db, pacient_id: int, user: str = "system") -> dict:
        from models.database import Pacient, Consultatie

        pacient = db.query(Pacient).filter(Pacient.id == pacient_id).first()
        if not pacient:
            return None

        consultatii = (
            db.query(Consultatie).filter(Consultatie.pacient_id == pacient_id).all()
        )
        export = {
            "export_date": datetime.utcnow().isoformat(),
            "gdpr_article": "Art. 15 + Art. 20",
            "pacient": {
                "id": pacient.id,
                "nume_complet": pacient.nume_complet,
                "cnp_masked": pacient.cnp_masked if pacient.cnp_masked else "N/A",
                "varsta": pacient.varsta,
                "istoric_medical": pacient.istoric_medical,
                "data_inregistrarii": str(pacient.data_inregistrarii),
                "consent_gdpr": pacient.consent_gdpr,
            },
            "consultatii": [
                {
                    "id": c.id,
                    "data": str(c.data_consultatiei),
                    "transcript": self.decrypt(c.transcript_audio) if c.transcript_audio else "",
                    "diagnostic_ai": self.decrypt(c.rezumat_diagnostic) if c.rezumat_diagnostic else "",
                    "corectie_medic": self.decrypt(c.raport_corectat_medic) if c.raport_corectat_medic else "",
                    "sugestii": c.sugestii_tratament,
                }
                for c in consultatii
            ],
        }
        self.log_access("DATA_EXPORT", user, f"Export date pacient ID {pacient_id}")
        return export


gdpr = GDPRManager()
