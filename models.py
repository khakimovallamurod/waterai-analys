from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(30), unique=True, index=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="user", nullable=False)  # "user" or "admin"
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    analyses = relationship("WaterAnalysis", back_populates="user", cascade="all, delete-orphan")


class WaterAnalysis(Base):
    __tablename__ = "water_analyses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    sample_name = Column(String(150), default="Suv namunasi", nullable=False)
    source_type = Column(String(50), default="Vodoprovod suvi", nullable=False)
    location = Column(String(100), default="Toshkent", nullable=True)

    # Parametrlar
    temperature = Column(Float, default=20.0, nullable=False)
    ph = Column(Float, default=7.0, nullable=False)
    tds = Column(Float, default=250.0, nullable=False)
    turbidity = Column(Float, default=1.0, nullable=False)
    ec = Column(Float, default=300.0, nullable=False)
    hardness = Column(Float, default=150.0, nullable=False)
    sulfate = Column(Float, default=100.0, nullable=False)
    chloramines = Column(Float, default=2.0, nullable=False)
    organic = Column(Float, default=2.0, nullable=False)
    trihalomethanes = Column(Float, default=10.0, nullable=False)
    extra_param = Column(String(50), default="Tanlang", nullable=True)

    # Tahlil natijalari
    status = Column(String(20), default="valid", nullable=False)  # "valid", "conditional", "invalid"
    status_label = Column(String(50), default="🟢 Yaroqli", nullable=False)
    quality_score = Column(Float, default=94.7, nullable=False)  # WQI 0-100
    confidence = Column(Float, default=94.7, nullable=False)
    prob_valid = Column(Float, default=94.7, nullable=False)
    prob_conditional = Column(Float, default=4.1, nullable=False)
    prob_invalid = Column(Float, default=1.2, nullable=False)
    bad_parameters_count = Column(Integer, default=0, nullable=False)
    status_text = Column(Text, nullable=True)
    ai_recommendation = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="analyses")


class ParameterNorm(Base):
    __tablename__ = "parameter_norms"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    unit = Column(String(30), nullable=False)
    norm_text = Column(String(50), nullable=False)
    min_val = Column(Float, nullable=True)
    max_val = Column(Float, nullable=True)
    importance_pct = Column(Float, default=10.0)
    description = Column(String(255), nullable=True)


class WaterSource(Base):
    __tablename__ = "water_sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    region = Column(String(100), nullable=False)
    city = Column(String(100), default="Samarqand", nullable=True)
    source_type = Column(String(50), default="Daryo suvi", nullable=False)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    status = Column(String(20), default="valid", nullable=False)  # "valid", "conditional", "invalid"
    status_label = Column(String(50), default="🟢 Yaroqli (Toza)", nullable=False)
    quality_score = Column(Float, default=90.0, nullable=False)
    ph = Column(Float, default=7.2, nullable=False)
    tds = Column(Float, default=250.0, nullable=False)
    turbidity = Column(Float, default=1.0, nullable=False)
    hardness = Column(Float, default=140.0, nullable=True)
    samples_count = Column(Integer, default=1, nullable=False)
    last_tested = Column(String(50), default="2026-09-27", nullable=True)
    desc = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

