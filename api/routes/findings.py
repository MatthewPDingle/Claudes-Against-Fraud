"""
Findings management routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
import uuid

from database import get_db
from models import Finding, Source, Evidence, Agent, User, Verification
from auth import get_current_user, get_agent_by_id

router = APIRouter(prefix="/findings", tags=["findings"])


# Pydantic schemas
class SourceCreate(BaseModel):
    url: str
    description: Optional[str] = None
    source_type: Optional[str] = None
    accessed_at: Optional[datetime] = None


class FindingCreate(BaseModel):
    agent_id: uuid.UUID
    discovery_task_id: Optional[uuid.UUID] = None
    title: str = Field(..., min_length=10, max_length=500)
    description: str = Field(..., min_length=100)
    category: str = Field(..., pattern="^(procurement|payroll|grants|contracts|infrastructure|other)$")
    jurisdiction: str = Field(..., min_length=1, max_length=100)
    estimated_amount: Optional[Decimal] = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    sources: List[SourceCreate] = Field(..., min_items=2)
    evidence: Optional[Dict[str, Any]] = None


class SourceResponse(BaseModel):
    source_id: uuid.UUID
    url: str
    description: Optional[str]
    source_type: Optional[str]
    verified: bool

    class Config:
        from_attributes = True


class VerificationSummary(BaseModel):
    total_verifications: int
    confirmed: int
    refuted: int
    uncertain: int
    consensus: Optional[str]


class FindingResponse(BaseModel):
    finding_id: uuid.UUID
    title: str
    description: str
    category: str
    jurisdiction: str
    estimated_amount: Optional[Decimal]
    confidence_score: Optional[Decimal]
    status: str
    created_at: datetime
    verified_at: Optional[datetime]
    published_at: Optional[datetime]
    sources: List[SourceResponse]
    verification_summary: Optional[VerificationSummary] = None

    class Config:
        from_attributes = True


class FindingListResponse(BaseModel):
    findings: List[FindingResponse]
    total: int
    page: int
    per_page: int
    pages: int


@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def submit_finding(
    finding: FindingCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Submit a new finding for verification
    """
    # Verify agent ownership
    agent = get_agent_by_id(str(finding.agent_id), db, user)

    # Validate sources
    if len(finding.sources) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least 2 sources required"
        )

    # Create finding
    db_finding = Finding(
        title=finding.title,
        description=finding.description,
        category=finding.category,
        jurisdiction=finding.jurisdiction,
        estimated_amount=finding.estimated_amount,
        confidence_score=finding.confidence,
        status="PENDING",
        discovered_by=agent.agent_id,
        discovery_task_id=finding.discovery_task_id,
        data={
            "evidence": finding.evidence or {},
            "agent_type": agent.agent_type,
            "submitted_at": datetime.utcnow().isoformat()
        }
    )

    db.add(db_finding)
    db.flush()

    # Create sources
    for source in finding.sources:
        db_source = Source(
            finding_id=db_finding.finding_id,
            url=source.url,
            description=source.description,
            source_type=source.source_type,
            accessed_at=source.accessed_at or datetime.utcnow()
        )
        db.add(db_source)

    # Update agent stats
    agent.findings_submitted += 1

    db.commit()
    db.refresh(db_finding)

    # TODO: Create verification tasks

    return {
        "finding_id": db_finding.finding_id,
        "status": db_finding.status,
        "next_step": "verification",
        "verification_tasks_created": 3,  # Placeholder
        "estimated_verification_time": "2-4 hours",
        "created_at": db_finding.created_at.isoformat()
    }


@router.get("/{finding_id}", response_model=FindingResponse)
async def get_finding(
    finding_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Get finding details
    """
    finding = db.query(Finding).filter(Finding.finding_id == finding_id).first()

    if not finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finding not found"
        )

    # Get verification summary
    verifications = db.query(Verification).filter(
        Verification.finding_id == finding.finding_id
    ).all()

    confirmed = sum(1 for v in verifications if v.verdict == "CONFIRMED")
    refuted = sum(1 for v in verifications if v.verdict == "REFUTED")
    uncertain = sum(1 for v in verifications if v.verdict == "UNCERTAIN")

    verification_summary = None
    if verifications:
        # Calculate consensus
        total = len(verifications)
        consensus = None
        if total >= 3:
            if confirmed / total >= 0.75:
                consensus = "STRONG_CONSENSUS_CONFIRMED"
            elif refuted / total >= 0.75:
                consensus = "STRONG_CONSENSUS_REFUTED"
            elif confirmed / total >= 0.6:
                consensus = "WEAK_CONSENSUS_CONFIRMED"
            elif refuted / total >= 0.6:
                consensus = "WEAK_CONSENSUS_REFUTED"
            else:
                consensus = "NO_CONSENSUS"

        verification_summary = VerificationSummary(
            total_verifications=total,
            confirmed=confirmed,
            refuted=refuted,
            uncertain=uncertain,
            consensus=consensus
        )

    return FindingResponse(
        **finding.__dict__,
        sources=[SourceResponse(**s.__dict__) for s in finding.sources],
        verification_summary=verification_summary
    )


@router.get("", response_model=FindingListResponse)
async def list_findings(
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    jurisdiction: Optional[str] = Query(None),
    min_amount: Optional[float] = Query(None),
    min_confidence: Optional[float] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    List findings with filtering and pagination
    """
    query = db.query(Finding)

    # Apply filters
    if status:
        query = query.filter(Finding.status == status)
    if category:
        query = query.filter(Finding.category == category)
    if jurisdiction:
        query = query.filter(Finding.jurisdiction == jurisdiction)
    if min_amount is not None:
        query = query.filter(Finding.estimated_amount >= min_amount)
    if min_confidence is not None:
        query = query.filter(Finding.confidence_score >= min_confidence)

    # Get total count
    total = query.count()

    # Apply pagination
    query = query.order_by(Finding.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)

    findings = query.all()

    # Calculate pages
    pages = (total + per_page - 1) // per_page

    return FindingListResponse(
        findings=[
            FindingResponse(
                **f.__dict__,
                sources=[SourceResponse(**s.__dict__) for s in f.sources],
                verification_summary=None
            )
            for f in findings
        ],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages
    )
