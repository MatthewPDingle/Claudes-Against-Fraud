"""
Agent management routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid

from database import get_db
from models import Agent, User
from auth import get_current_user, get_agent_by_id

router = APIRouter(prefix="/agents", tags=["agents"])


# Pydantic schemas
class AgentCreate(BaseModel):
    agent_name: str = Field(..., min_length=1, max_length=100)
    agent_type: str = Field(..., pattern="^(discovery|verification|documentation)$")
    capabilities: List[str] = Field(default=[])
    metadata: dict = Field(default={})


class AgentResponse(BaseModel):
    agent_id: uuid.UUID
    agent_name: str
    agent_type: str
    trust_score: float
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class AgentStats(BaseModel):
    tasks_completed: int
    success_rate: float
    findings_submitted: int
    findings_verified: int
    findings_published: int
    findings_retracted: int
    total_amount_flagged: float
    verifications_submitted: int
    verification_accuracy: Optional[float]
    average_confidence: float


class AgentDetail(AgentResponse):
    capabilities: List[str]
    stats: AgentStats
    last_active: Optional[datetime]


class HeartbeatRequest(BaseModel):
    status: str = Field(..., pattern="^(idle|working)$")
    current_task_id: Optional[uuid.UUID] = None
    progress: float = Field(default=0.0, ge=0.0, le=1.0)


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def register_agent(
    agent: AgentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Register a new agent
    """
    # Check if agent name already exists for this user
    existing = db.query(Agent).filter(
        Agent.user_id == user.user_id,
        Agent.agent_name == agent.agent_name
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Agent name already exists"
        )

    # Create agent
    db_agent = Agent(
        user_id=user.user_id,
        agent_name=agent.agent_name,
        agent_type=agent.agent_type,
        capabilities=agent.capabilities,
        trust_score=0.50,  # Start with neutral trust
        metadata=agent.metadata
    )

    db.add(db_agent)
    db.commit()
    db.refresh(db_agent)

    return db_agent


@router.get("/{agent_id}", response_model=AgentDetail)
async def get_agent(
    agent_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Get agent details
    """
    agent = get_agent_by_id(agent_id, db, user)

    # Calculate stats
    stats = AgentStats(
        tasks_completed=agent.tasks_completed or 0,
        success_rate=(
            agent.tasks_completed / (agent.tasks_completed + agent.tasks_failed)
            if (agent.tasks_completed + agent.tasks_failed) > 0
            else 0.0
        ),
        findings_submitted=agent.findings_submitted or 0,
        findings_verified=agent.findings_verified or 0,
        findings_published=agent.findings_verified or 0,  # Simplified
        findings_retracted=agent.findings_retracted or 0,
        total_amount_flagged=0.0,  # TODO: Calculate from findings
        verifications_submitted=agent.verifications_submitted or 0,
        verification_accuracy=float(agent.verification_accuracy) if agent.verification_accuracy else None,
        average_confidence=0.0  # TODO: Calculate from findings
    )

    return AgentDetail(
        **agent.__dict__,
        stats=stats
    )


@router.post("/{agent_id}/heartbeat")
async def send_heartbeat(
    agent_id: str,
    heartbeat: HeartbeatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Send agent heartbeat to keep status active
    """
    agent = get_agent_by_id(agent_id, db, user)

    # Update heartbeat
    agent.last_heartbeat = datetime.utcnow()
    agent.last_active = datetime.utcnow()

    if agent.status == "INACTIVE":
        agent.status = "ACTIVE"

    db.commit()

    return {
        "acknowledged": True,
        "server_time": datetime.utcnow().isoformat()
    }


@router.get("", response_model=List[AgentResponse])
async def list_agents(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    List all agents for current user
    """
    agents = db.query(Agent).filter(Agent.user_id == user.user_id).all()
    return agents
