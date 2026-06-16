from pydantic import BaseModel


class PacientNou(BaseModel):
    nume_complet: str
    cnp: str
    varsta: int
    istoric_medical: str = ""
