import uuid
from sqlalchemy import Column, String, JSON, Float, ForeignKey, Integer, UniqueConstraint, Index, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from .base import Base, TimestampMixin


class RawProject(Base, TimestampMixin):
    __tablename__ = "raw_projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(String, nullable=False)
    source_id = Column(String, nullable=False)
    fetched_at = Column(DateTime, nullable=False)
    raw_payload = Column(JSON, nullable=False)
    status = Column(String, nullable=False, default="RECEIVED")
    error_detail = Column(String)

    __table_args__ = (
        UniqueConstraint("source", "source_id", name="uq_raw_projects_source_source_id"),
        Index("ix_raw_projects_source", "source"),
        Index("ix_raw_projects_status", "status"),
    )


class RawContractor(Base, TimestampMixin):
    __tablename__ = "raw_contractors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(String, nullable=False)
    source_id = Column(String, nullable=False)
    fetched_at = Column(DateTime, nullable=False)
    raw_payload = Column(JSON, nullable=False)
    status = Column(String, nullable=False, default="RECEIVED")
    error_detail = Column(String)

    __table_args__ = (
        UniqueConstraint("source", "source_id", name="uq_raw_contractors_source_source_id"),
        Index("ix_raw_contractors_source", "source"),
        Index("ix_raw_contractors_status", "status"),
    )


class IngestionRun(Base, TimestampMixin):
    __tablename__ = "ingestion_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(String, nullable=False)
    started_at = Column(DateTime, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String, nullable=False, default="RUNNING")
    records_fetched = Column(Integer, nullable=False, default=0)
    accepted = Column(Integer, nullable=False, default=0)
    rejected = Column(Integer, nullable=False, default=0)
    duplicates = Column(Integer, nullable=False, default=0)
    errors = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        Index("ix_ingestion_runs_source", "source"),
        Index("ix_ingestion_runs_status", "status"),
    )


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    source = Column(String, nullable=False)
    source_id = Column(String, nullable=False)
    city = Column(String)
    state = Column(String(2))
    latitude = Column(Float)
    longitude = Column(Float)
    trades = Column(JSON)
    bid_date = Column(String)
    posted_date = Column(String)
    response_deadline = Column(String)
    status = Column(String)
    description = Column(String)
    source_url = Column(String)
    estimated_value = Column(Float)
    provenance = Column(JSON)

    __table_args__ = (
        UniqueConstraint("source", "source_id", name="uq_projects_source_source_id"),
        Index("ix_projects_source", "source"),
        Index("ix_projects_source_id", "source_id"),
    )


class Contractor(Base, TimestampMixin):
    __tablename__ = "contractors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_name = Column(String, nullable=False)
    normalized_name = Column(String)
    source = Column(String, nullable=False)
    source_id = Column(String, nullable=False)
    city = Column(String)
    state = Column(String(2))
    trades = Column(JSON)
    primary_email = Column(String)
    provenance = Column(JSON)

    __table_args__ = (
        UniqueConstraint("source", "source_id", name="uq_contractors_source_source_id"),
        Index("ix_contractors_source", "source"),
        Index("ix_contractors_source_id", "source_id"),
    )


class MatchRecord(Base, TimestampMixin):
    __tablename__ = "match_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    contractor_id = Column(UUID(as_uuid=True), ForeignKey("contractors.id"), nullable=False)
    match_score = Column(Float, nullable=False)
    raw_score = Column(Float, nullable=False, default=0.0)
    max_available_score = Column(Float, nullable=False, default=0.0)
    feature_completeness = Column(Float, nullable=False, default=0.0)
    confidence = Column(String, nullable=False)
    matcher_version = Column(String, nullable=False)
    ranking = Column(Integer, nullable=False, default=0)
    positive_factors = Column(JSON, default=list)
    negative_factors = Column(JSON, default=list)
    unknown_factors = Column(JSON, default=list)
    components = Column(JSON, default=dict)
    review_status = Column(String, nullable=False, default="UNREVIEWED")
    reviewed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("project_id", "contractor_id", "matcher_version", name="uq_match_records_project_contractor_version"),
        Index("ix_match_records_project_id", "project_id"),
        Index("ix_match_records_contractor_id", "contractor_id"),
        Index("ix_match_records_review_status", "review_status"),
    )


class MatchReviewAudit(Base, TimestampMixin):
    __tablename__ = "match_review_audit"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    match_id = Column(UUID(as_uuid=True), ForeignKey("match_records.id"), nullable=False)
    previous_status = Column(String, nullable=False)
    new_status = Column(String, nullable=False)
    actor = Column(String, nullable=False, default="local-dev")
    source = Column(String, nullable=False, default="local-dev")

    __table_args__ = (
        Index("ix_match_review_audit_match_id", "match_id"),
    )



class OutreachDraft(Base, TimestampMixin):
    __tablename__ = "outreach_drafts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    match_id = Column(UUID(as_uuid=True), ForeignKey("match_records.id"), nullable=False)
    template_version = Column(String, nullable=False)
    recipient_email = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    body = Column(String, nullable=False)
    status = Column(String, nullable=False, default="DRAFT")
    generated_at = Column(DateTime, nullable=False, server_default=func.now())
    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(String, nullable=True)
    provenance = Column(JSON, default=dict)

    __table_args__ = (
        UniqueConstraint("match_id", "template_version", name="uq_outreach_drafts_match_template"),
        Index("ix_outreach_drafts_match_id", "match_id"),
        Index("ix_outreach_drafts_status", "status"),
    )


class OutreachDraftAudit(Base, TimestampMixin):
    __tablename__ = "outreach_draft_audit"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    draft_id = Column(UUID(as_uuid=True), ForeignKey("outreach_drafts.id"), nullable=False)
    previous_status = Column(String, nullable=False)
    new_status = Column(String, nullable=False)
    actor = Column(String, nullable=False, default="local-dev")
    source = Column(String, nullable=False, default="local-dev")

    __table_args__ = (
        Index("ix_outreach_draft_audit_draft_id", "draft_id"),
    )
