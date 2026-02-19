"""SQLAlchemy models for procurement data."""

from datetime import datetime

from sqlalchemy import (
    ARRAY,
    DECIMAL,
    Column,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Procurement(Base):
    __tablename__ = "procurements"

    id = Column(Integer, primary_key=True)
    notice_id = Column(Text, nullable=False, unique=True)
    procurement_id = Column(Text)
    title = Column(Text, nullable=False)
    description = Column(Text)
    contracting_auth = Column(Text, nullable=False)
    contracting_auth_reg = Column(Text)
    contract_type = Column(Text)  # ehitustööd / teenused / tarned
    procedure_type = Column(Text)  # lihthange / avatud / etc.
    cpv_primary = Column(Text)
    cpv_additional = Column(ARRAY(Text), default=list)
    estimated_value = Column(DECIMAL(12, 2))
    nuts_code = Column(Text)
    nuts_name = Column(Text)
    submission_deadline = Column(DateTime(timezone=True))
    publication_date = Column(DateTime(timezone=True))
    duration_months = Column(Integer)
    status = Column(Text, default="active")  # active / expired / awarded
    source_url = Column(Text)
    raw_html = Column(Text)
    trade_tags = Column(ARRAY(Text), default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_procurements_cpv", "cpv_primary"),
        Index("idx_procurements_status", "status"),
        Index("idx_procurements_deadline", "submission_deadline"),
        Index("idx_procurements_trade", "trade_tags", postgresql_using="gin"),
    )


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id = Column(Integer, primary_key=True)
    run_type = Column(Text, nullable=False)  # bulk_xml / notice_html / status_update
    year_month = Column(Text)
    notices_found = Column(Integer, default=0)
    notices_stored = Column(Integer, default=0)
    notices_skipped = Column(Integer, default=0)
    errors = Column(Integer, default=0)
    duration_ms = Column(Integer)
    status = Column(Text, default="running")  # running / completed / failed
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TradeCpvMapping(Base):
    __tablename__ = "trade_cpv_mappings"

    id = Column(Integer, primary_key=True)
    cpv_prefix = Column(Text, nullable=False)
    trade_key = Column(Text, nullable=False)
    trade_name_et = Column(Text, nullable=False)
    trade_name_en = Column(Text, nullable=False)
