from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime, timezone

def _utcnow():
    return datetime.now(timezone.utc)

SQLALCHEMY_DATABASE_URL = "sqlite:///./cabinet.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Pacient(Base):
    __tablename__ = "pacienti"

    id = Column(Integer, primary_key=True, index=True)
    nume_complet = Column(String, index=True)
    cnp = Column(String, unique=True, index=True)  # SHA-256 hash
    cnp_masked = Column(String, default="")
    varsta = Column(Integer)
    istoric_medical = Column(Text, default="")
    data_inregistrarii = Column(DateTime, default=_utcnow)
    consent_gdpr = Column(Boolean, default=False)
    data_consent = Column(DateTime, nullable=True)

    consultatii = relationship("Consultatie", back_populates="pacient")


class Consultatie(Base):
    __tablename__ = "consultatii"

    id = Column(Integer, primary_key=True, index=True)
    pacient_id = Column(Integer, ForeignKey("pacienti.id"))
    data_consultatiei = Column(DateTime, default=_utcnow)
    transcript_audio = Column(Text)
    rezumat_diagnostic = Column(Text)
    raport_corectat_medic = Column(Text, nullable=True)
    utilizat_pentru_fl = Column(Integer, default=0)
    sugestii_tratament = Column(Text)

    pacient = relationship("Pacient", back_populates="consultatii")


def creaza_tabele():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
