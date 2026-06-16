import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models.database import get_db, Pacient
from services.gdpr_service import gdpr

router = APIRouter(prefix="/gdpr", tags=["GDPR"])


@router.delete("/pacienti/{pacient_id}")
def gdpr_sterge_pacient(pacient_id: int, db: Session = Depends(get_db)):
    """GDPR Art. 17 — Right to Erasure."""
    result = gdpr.sterge_date_pacient(db, pacient_id, user="medic")
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])
    return result


@router.get("/pacienti/{pacient_id}/export")
def gdpr_export_pacient(pacient_id: int, db: Session = Depends(get_db)):
    """GDPR Art. 15 + 20 — Right of Access & Data Portability."""
    export = gdpr.export_date_pacient(db, pacient_id, user="medic")
    if not export:
        raise HTTPException(status_code=404, detail="Pacientul nu exista.")
    return export


@router.get("/audit-log")
def gdpr_audit_log(limit: int = 50):
    """GDPR Art. 30 — Evidenta activitatilor de prelucrare."""
    return {"entries": gdpr.get_audit_log(limit=limit)}


@router.get("/status")
def gdpr_status(db: Session = Depends(get_db)):
    """Statusul conformitatii GDPR a sistemului."""
    total_pacienti = db.query(Pacient).count()
    cu_consent = db.query(Pacient).filter(Pacient.consent_gdpr == True).count()  # noqa: E712
    return {
        "criptare_activa": bool(os.getenv("ENCRYPTION_KEY")),
        "salt_cnp_configurat": not os.getenv("CNP_SALT", "").startswith("medical_ai_default"),
        "total_pacienti": total_pacienti,
        "cu_consent_gdpr": cu_consent,
        "fara_consent": total_pacienti - cu_consent,
        "articole_implementate": [
            "Art. 5  — Pseudonimizare (hash CNP)",
            "Art. 6  — Consent explicit la inregistrare",
            "Art. 15 — Dreptul de acces (GET /gdpr/pacienti/{id}/export)",
            "Art. 17 — Dreptul la stergere (DELETE /gdpr/pacienti/{id})",
            "Art. 20 — Portabilitatea datelor (export JSON)",
            "Art. 25 — Privacy by Design (criptare AES-256)",
            "Art. 30 — Evidenta prelucrarilor (audit log)",
            "Art. 32 — Securitate (criptare at rest)",
        ],
    }
