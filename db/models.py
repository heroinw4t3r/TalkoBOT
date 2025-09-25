import json
import datetime as dt
from sqlalchemy import Integer, String, DateTime, Boolean, Text, Float, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from shared.db import Base

class Form(Base):
    __tablename__ = "forms"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tg_user_id: Mapped[int] = mapped_column(Integer, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    age: Mapped[str] = mapped_column(String(32))
    timezone: Mapped[str] = mapped_column(String(64))
    city: Mapped[str] = mapped_column(String(128), default="")
    tg_username: Mapped[str] = mapped_column(String(255))
    alt_contact: Mapped[str] = mapped_column(Text, default="")
    level: Mapped[str] = mapped_column(String(64))
    participated_before: Mapped[str] = mapped_column(String(8))  # Да/Нет
    priority: Mapped[str] = mapped_column(String(255))
    hobbies: Mapped[str] = mapped_column(Text)
    goals: Mapped[str] = mapped_column(Text, default="")
    topics: Mapped[str] = mapped_column(Text)
    days: Mapped[str] = mapped_column(Text)  # JSON list
    time_of_day: Mapped[str] = mapped_column(String(32))
    schedule_strictness: Mapped[str] = mapped_column(String(64))
    initiative: Mapped[str] = mapped_column(String(64))
    preferred_partner_gender: Mapped[str] = mapped_column(String(32))
    other_notes: Mapped[str] = mapped_column(Text, default="")
    accepted_rules: Mapped[bool] = mapped_column(Boolean)
    accepted_offer: Mapped[bool] = mapped_column(Boolean)
    accepted_nda: Mapped[bool] = mapped_column(Boolean)
    repost_photo_file_id: Mapped[str] = mapped_column(String(255), default="")
    in_project: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    def days_list(self) -> list[str]:
        try:
            return json.loads(self.days or "[]")
        except Exception:
            return []

class PasswordState(Base):
    __tablename__ = "password_state"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    version_key: Mapped[str] = mapped_column(String(12), index=True)  # YYYYMMDDHH
    value: Mapped[str] = mapped_column(String(64))
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)


class StudyBuddy(Base):
    __tablename__ = "study_buddies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    form1_id: Mapped[int] = mapped_column(Integer, index=True)
    form2_id: Mapped[int] = mapped_column(Integer, index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)


class Discount(Base):
    __tablename__ = "discounts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_identifier: Mapped[str] = mapped_column(String(255), index=True)
    percent: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)
    __table_args__ = (
        UniqueConstraint('user_identifier', name='uq_discounts_user_identifier'),
    )