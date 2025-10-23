from datetime import date
from sqlalchemy import Integer, String, Date, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from db import Base

class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(120), default="")
    country: Mapped[str] = mapped_column(String(120), default="")
    location: Mapped[str] = mapped_column(String(255), default="")
    posting_date: Mapped[date] = mapped_column(Date, nullable=False)
    job_type: Mapped[str] = mapped_column(String(60), default="Full-time")
    tags: Mapped[list] = mapped_column(JSONB, default=list)  # list[str]
    job_url: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (UniqueConstraint("job_url", name="uq_jobs_job_url"),)
