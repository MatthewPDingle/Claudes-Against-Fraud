"""
Task management routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid

from database import get_db
from models import Task, Agent, User
from auth import get_current_user, get_agent_by_id

router = APIRouter(prefix="/tasks", tags=["tasks"])


# Pydantic schemas
class TaskPreferences(BaseModel):
    categories: Optional[List[str]] = None
    jurisdictions: Optional[List[str]] = None
    min_priority: int = Field(default=0, ge=0, le=100)


class TaskClaimRequest(BaseModel):
    agent_id: uuid.UUID
    agent_type: str
    preferences: Optional[TaskPreferences] = None


class TaskResponse(BaseModel):
    task_id: uuid.UUID
    task_type: str
    priority: int
    data_source: Optional[str]
    target_entity: Optional[str]
    deadline: Optional[datetime]
    payload: Dict[str, Any]
    claimed_at: datetime

    class Config:
        from_attributes = True


class TaskCompleteRequest(BaseModel):
    agent_id: uuid.UUID
    status: str = Field(..., pattern="^(COMPLETED|FAILED)$")
    result: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class TaskCompleteResponse(BaseModel):
    task_id: uuid.UUID
    status: str
    findings_created: List[uuid.UUID] = []
    trust_score_delta: float
    new_trust_score: float


class TaskFailRequest(BaseModel):
    agent_id: uuid.UUID
    error_type: str
    error_message: str
    retry_recommended: bool = True


@router.post("/claim", response_model=Optional[TaskResponse], status_code=status.HTTP_200_OK)
async def claim_task(
    request: TaskClaimRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Claim next available task from queue
    """
    # Verify agent ownership
    agent = get_agent_by_id(str(request.agent_id), db, user)

    # Build query for available tasks
    query = db.query(Task).filter(
        Task.status == "PENDING",
        Task.task_type.in_(["DISCOVERY", "VERIFICATION", "DOCUMENTATION", "ANALYSIS"])
    )

    # Apply preferences
    if request.preferences:
        if request.preferences.min_priority:
            query = query.filter(Task.priority >= request.preferences.min_priority)

        # TODO: Filter by categories and jurisdictions from payload

    # Order by priority
    query = query.order_by(Task.priority.desc(), Task.created_at.asc())

    # Get first available task
    task = query.first()

    if not task:
        # No tasks available
        return None

    # Claim task
    task.status = "CLAIMED"
    task.assigned_to = agent.agent_id
    task.claimed_at = datetime.utcnow()

    # Set deadline (e.g., 4 hours from now)
    task.deadline = datetime.utcnow() + timedelta(hours=4)

    db.commit()
    db.refresh(task)

    return task


@router.post("/{task_id}/complete", response_model=TaskCompleteResponse)
async def complete_task(
    task_id: str,
    request: TaskCompleteRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Submit completed task results
    """
    # Verify agent ownership
    agent = get_agent_by_id(str(request.agent_id), db, user)

    # Get task
    task = db.query(Task).filter(Task.task_id == task_id).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Verify task is assigned to this agent
    if task.assigned_to != agent.agent_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Task not assigned to this agent"
        )

    # Update task
    task.status = request.status
    task.completed_at = datetime.utcnow()
    task.result = request.result

    # Update agent stats
    if request.status == "COMPLETED":
        agent.tasks_completed += 1

        # Small trust score increase for completing tasks
        trust_delta = 0.01
        agent.trust_score = min(1.0, float(agent.trust_score) + trust_delta)
    else:
        agent.tasks_failed += 1
        trust_delta = 0.0

    db.commit()

    # TODO: Process findings from result
    findings_created = []

    return TaskCompleteResponse(
        task_id=task.task_id,
        status=task.status,
        findings_created=findings_created,
        trust_score_delta=trust_delta,
        new_trust_score=float(agent.trust_score)
    )


@router.post("/{task_id}/fail")
async def fail_task(
    task_id: str,
    request: TaskFailRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Report task failure
    """
    # Verify agent ownership
    agent = get_agent_by_id(str(request.agent_id), db, user)

    # Get task
    task = db.query(Task).filter(Task.task_id == task_id).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Verify task is assigned to this agent
    if task.assigned_to != agent.agent_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Task not assigned to this agent"
        )

    # Update task
    task.status = "FAILED"
    task.error_message = f"{request.error_type}: {request.error_message}"
    task.completed_at = datetime.utcnow()

    # Handle retry
    if request.retry_recommended and task.retry_count < task.max_retries:
        task.retry_count += 1
        task.status = "PENDING"
        task.assigned_to = None
        task.claimed_at = None
        task.completed_at = None
        # Increase priority for retries
        task.priority = min(100, task.priority + 10)

    # Update agent stats
    agent.tasks_failed += 1

    db.commit()

    return {"status": "acknowledged"}
