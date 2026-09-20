from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.core import Contractor, MatchRecord, OutreachDraft, Project

TEMPLATE_VERSION = "deterministic-v1"


def _coerce_uuid(value: Any, field_name: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid {field_name}: {value}") from exc


def _trade_text(project: Project) -> str:
    trades = project.trades or []
    if isinstance(trades, str):
        return trades
    if isinstance(trades, list):
        return ", ".join(str(item) for item in trades if item)
    return str(trades) if trades else "construction"


def build_outreach_draft(session: Session, match_id: str, actor: str = "local-dev", source: str = "local-dev") -> OutreachDraft:
    match_uuid = _coerce_uuid(match_id, "match_id")
    match = session.get(MatchRecord, match_uuid)
    if match is None:
        raise ValueError(f"Match not found: {match_id}")
    if match.review_status != "APPROVED":
        raise ValueError("Match must be APPROVED before an outreach draft can be generated")

    project = session.get(Project, match.project_id)
    contractor = session.get(Contractor, match.contractor_id)
    if project is None or contractor is None:
        raise ValueError("Match project or contractor is missing")
    if not contractor.primary_email or not contractor.primary_email.strip():
        raise ValueError("Contractor has no primary email")

    existing = session.execute(
        select(OutreachDraft).where(
            OutreachDraft.match_id == match.id,
            OutreachDraft.template_version == TEMPLATE_VERSION,
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    location = ", ".join(part for part in [project.city, project.state] if part) or "your area"
    subject = f"Estimating support for {project.name}"
    body = (
        f"Hi {contractor.company_name},\\n\\n"
        f"I’m reaching out regarding {project.name} in {location}. "
        f"ACE Services provides construction estimating and quantity takeoff support, including {_trade_text(project)}.\\n\\n"
        "If your team needs additional estimating capacity for this opportunity, we can review the plans and provide a bid-ready estimate. "
        "Reply to this email if you’d like to discuss the project and next steps.\\n\\n"
        "Best,\\nACE Services"
    )
    draft = OutreachDraft(
        match_id=match.id,
        template_version=TEMPLATE_VERSION,
        recipient_email=contractor.primary_email.strip(),
        subject=subject,
        body=body,
        status="DRAFT",
        approved_by=None,
        provenance={
            "generator": "deterministic-template",
            "template_version": TEMPLATE_VERSION,
            "actor": actor,
            "source": source,
        },
    )
    session.add(draft)
    session.flush()
    return draft
