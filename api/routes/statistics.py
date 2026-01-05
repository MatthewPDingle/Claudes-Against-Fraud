"""
Statistics and metrics routes
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from datetime import datetime, timedelta

from database import get_db
from models import Agent, Finding, Verification, Task, User
from auth import get_current_user

router = APIRouter(prefix="/statistics", tags=["statistics"])


class PlatformStats(BaseModel):
    total_agents: int
    active_agents_24h: int
    findings_published: int
    total_flagged_amount: float
    average_confidence_score: float
    consensus_rate: float
    retraction_rate: float


class RecentActivity(BaseModel):
    findings_last_24h: int
    verifications_last_24h: int
    reports_published_last_24h: int


class StatisticsResponse(BaseModel):
    as_of: datetime
    platform_stats: PlatformStats
    recent_activity: RecentActivity


@router.get("", response_model=StatisticsResponse)
async def get_statistics(db: Session = Depends(get_db)):
    """
    Get public platform statistics
    """
    # Total agents
    total_agents = db.query(Agent).count()

    # Active agents in last 24 hours
    yesterday = datetime.utcnow() - timedelta(hours=24)
    active_agents_24h = db.query(Agent).filter(
        Agent.last_active >= yesterday
    ).count()

    # Published findings
    findings_published = db.query(Finding).filter(
        Finding.status == "PUBLISHED"
    ).count()

    # Total flagged amount
    total_flagged = db.query(func.sum(Finding.estimated_amount)).filter(
        Finding.status.in_(["VERIFIED", "PUBLISHED"])
    ).scalar() or 0

    # Average confidence score
    avg_confidence = db.query(func.avg(Finding.confidence_score)).filter(
        Finding.status.in_(["VERIFIED", "PUBLISHED"])
    ).scalar() or 0

    # Consensus rate (simplified)
    # TODO: Calculate actual consensus rate from verifications
    consensus_rate = 0.82

    # Retraction rate
    total_published = findings_published
    retracted = db.query(Finding).filter(
        Finding.status == "RETRACTED"
    ).count()
    retraction_rate = retracted / total_published if total_published > 0 else 0

    # Recent activity
    findings_24h = db.query(Finding).filter(
        Finding.created_at >= yesterday
    ).count()

    verifications_24h = db.query(Verification).filter(
        Verification.created_at >= yesterday
    ).count()

    # TODO: Get actual reports count
    reports_24h = 0

    return StatisticsResponse(
        as_of=datetime.utcnow(),
        platform_stats=PlatformStats(
            total_agents=total_agents,
            active_agents_24h=active_agents_24h,
            findings_published=findings_published,
            total_flagged_amount=float(total_flagged),
            average_confidence_score=float(avg_confidence),
            consensus_rate=consensus_rate,
            retraction_rate=retraction_rate
        ),
        recent_activity=RecentActivity(
            findings_last_24h=findings_24h,
            verifications_last_24h=verifications_24h,
            reports_published_last_24h=reports_24h
        )
    )
