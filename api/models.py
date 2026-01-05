"""
SQLAlchemy ORM models for Claudes Against Fraud
"""
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text,
    ForeignKey, ARRAY, JSON, BigInteger, Numeric, Date, Index
)
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid

from database import Base


class User(Base):
    """User account"""
    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    email_verified = Column(Boolean, default=False)
    github_username = Column(String(100))
    github_id = Column(String(100))
    trust_level = Column(String(20), default="NEWCOMER")
    status = Column(String(20), default="ACTIVE")
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    suspension_end = Column(DateTime)
    suspension_reason = Column(Text)
    metadata = Column(JSON, default={})

    # Relationships
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    agents = relationship("Agent", back_populates="user", cascade="all, delete-orphan")


class APIKey(Base):
    """API key for authentication"""
    __tablename__ = "api_keys"

    key_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    key_hash = Column(String(64), unique=True, nullable=False)
    key_name = Column(String(100))
    scopes = Column(ARRAY(String), default=["read", "write:findings", "write:verifications"])
    rate_limit_tier = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    last_used = Column(DateTime)
    revoked = Column(Boolean, default=False)
    revoked_at = Column(DateTime)
    ip_whitelist = Column(ARRAY(INET))

    # Relationships
    user = relationship("User", back_populates="api_keys")

    # Indexes
    __table_args__ = (
        Index("idx_api_keys_user", "user_id"),
        Index("idx_api_keys_hash", "key_hash", postgresql_where=Column("revoked") == False),
    )


class Agent(Base):
    """Agent instance"""
    __tablename__ = "agents"

    agent_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    agent_name = Column(String(100), nullable=False)
    agent_type = Column(String(50), nullable=False)
    capabilities = Column(ARRAY(String), default=[])
    trust_score = Column(Numeric(3, 2), default=0.50)
    tasks_completed = Column(Integer, default=0)
    tasks_failed = Column(Integer, default=0)
    findings_submitted = Column(Integer, default=0)
    findings_verified = Column(Integer, default=0)
    findings_retracted = Column(Integer, default=0)
    verifications_submitted = Column(Integer, default=0)
    verification_accuracy = Column(Numeric(3, 2))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    last_heartbeat = Column(DateTime)
    status = Column(String(20), default="ACTIVE")
    metadata = Column(JSON, default={})

    # Relationships
    user = relationship("User", back_populates="agents")
    tasks = relationship("Task", back_populates="agent", foreign_keys="Task.assigned_to")
    findings = relationship("Finding", back_populates="discoverer", foreign_keys="Finding.discovered_by")
    verifications = relationship("Verification", back_populates="agent")

    # Indexes
    __table_args__ = (
        Index("idx_agents_user", "user_id"),
        Index("idx_agents_active", "status", "last_active"),
        Index("idx_agents_trust", "trust_score"),
    )


class Task(Base):
    """Investigation task"""
    __tablename__ = "tasks"

    task_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_type = Column(String(50), nullable=False)
    priority = Column(Integer, default=50)
    status = Column(String(20), default="PENDING")
    data_source = Column(String(200))
    target_entity = Column(String(500))
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("agents.agent_id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    claimed_at = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    deadline = Column(DateTime)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    dependencies = Column(ARRAY(UUID))
    payload = Column(JSON, nullable=False)
    result = Column(JSON)
    error_message = Column(Text)

    # Relationships
    agent = relationship("Agent", back_populates="tasks", foreign_keys=[assigned_to])

    # Indexes
    __table_args__ = (
        Index("idx_tasks_status", "status", "priority"),
        Index("idx_tasks_assigned", "assigned_to", "status"),
        Index("idx_tasks_type", "task_type"),
        Index("idx_tasks_created", "created_at"),
    )


class Finding(Base):
    """Fraud finding"""
    __tablename__ = "findings"

    finding_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(50), nullable=False)
    jurisdiction = Column(String(100), nullable=False)
    estimated_amount = Column(Numeric(15, 2))
    confidence_score = Column(Numeric(3, 2))
    status = Column(String(20), default="PENDING")
    discovered_by = Column(UUID(as_uuid=True), ForeignKey("agents.agent_id"), nullable=False)
    discovery_task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.task_id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    verified_at = Column(DateTime)
    published_at = Column(DateTime)
    retracted_at = Column(DateTime)
    retraction_reason = Column(Text)
    view_count = Column(Integer, default=0)
    data = Column(JSON, nullable=False)

    # Relationships
    discoverer = relationship("Agent", back_populates="findings", foreign_keys=[discovered_by])
    sources = relationship("Source", back_populates="finding", cascade="all, delete-orphan")
    evidence = relationship("Evidence", back_populates="finding", cascade="all, delete-orphan")
    verifications = relationship("Verification", back_populates="finding", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="finding")

    # Indexes
    __table_args__ = (
        Index("idx_findings_status", "status"),
        Index("idx_findings_category", "category"),
        Index("idx_findings_jurisdiction", "jurisdiction"),
        Index("idx_findings_amount", "estimated_amount"),
        Index("idx_findings_confidence", "confidence_score"),
        Index("idx_findings_created", "created_at"),
    )


class Source(Base):
    """Source for a finding"""
    __tablename__ = "sources"

    source_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    finding_id = Column(UUID(as_uuid=True), ForeignKey("findings.finding_id", ondelete="CASCADE"), nullable=False)
    url = Column(Text, nullable=False)
    description = Column(Text)
    source_type = Column(String(50))
    credibility_score = Column(Numeric(3, 2))
    accessed_at = Column(DateTime, default=datetime.utcnow)
    archived_url = Column(Text)
    verified = Column(Boolean, default=False)
    verified_at = Column(DateTime)
    metadata = Column(JSON, default={})

    # Relationships
    finding = relationship("Finding", back_populates="sources")

    # Indexes
    __table_args__ = (
        Index("idx_sources_finding", "finding_id"),
    )


class Evidence(Base):
    """Evidence for a finding"""
    __tablename__ = "evidence"

    evidence_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    finding_id = Column(UUID(as_uuid=True), ForeignKey("findings.finding_id", ondelete="CASCADE"), nullable=False)
    evidence_type = Column(String(50), nullable=False)
    description = Column(Text)
    storage_path = Column(Text, nullable=False)
    file_size = Column(BigInteger)
    mime_type = Column(String(100))
    file_hash = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)
    metadata = Column(JSON, default={})

    # Relationships
    finding = relationship("Finding", back_populates="evidence")

    # Indexes
    __table_args__ = (
        Index("idx_evidence_finding", "finding_id"),
        Index("idx_evidence_hash", "file_hash"),
    )


class Verification(Base):
    """Verification of a finding"""
    __tablename__ = "verifications"

    verification_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    finding_id = Column(UUID(as_uuid=True), ForeignKey("findings.finding_id", ondelete="CASCADE"), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.agent_id"), nullable=False)
    verification_task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.task_id"))
    verdict = Column(String(20), nullable=False)
    confidence = Column(Numeric(3, 2))
    notes = Column(Text)
    additional_sources = Column(JSON)
    flags = Column(ARRAY(String))
    created_at = Column(DateTime, default=datetime.utcnow)
    time_spent_seconds = Column(Integer)

    # Relationships
    finding = relationship("Finding", back_populates="verifications")
    agent = relationship("Agent", back_populates="verifications")

    # Indexes
    __table_args__ = (
        Index("idx_verifications_finding", "finding_id"),
        Index("idx_verifications_agent", "agent_id"),
        Index("idx_verifications_verdict", "verdict"),
    )


class Report(Base):
    """Published report"""
    __tablename__ = "reports"

    report_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    finding_id = Column(UUID(as_uuid=True), ForeignKey("findings.finding_id"), nullable=False)
    report_type = Column(String(50), default="standard")
    version = Column(Integer, default=1)
    published_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime)
    public_url = Column(Text)
    archived_hash = Column(Text)
    view_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)
    feedback_count = Column(Integer, default=0)
    content = Column(JSON, nullable=False)
    metadata = Column(JSON, default={})

    # Relationships
    finding = relationship("Finding", back_populates="reports")

    # Indexes
    __table_args__ = (
        Index("idx_reports_finding", "finding_id"),
        Index("idx_reports_published", "published_at"),
    )


class AuditLog(Base):
    """Audit log entry"""
    __tablename__ = "audit_log"

    log_id = Column(BigInteger, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    event_type = Column(String(50), nullable=False)
    actor_type = Column(String(20), nullable=False)
    actor_id = Column(UUID(as_uuid=True))
    action = Column(String(100), nullable=False)
    target_type = Column(String(50))
    target_id = Column(UUID(as_uuid=True))
    ip_address_hash = Column(String(64))
    metadata = Column(JSON)
    previous_log_hash = Column(String(64))

    # Indexes
    __table_args__ = (
        Index("idx_audit_log_timestamp", "timestamp"),
        Index("idx_audit_log_actor", "actor_id", "timestamp"),
        Index("idx_audit_log_event", "event_type", "timestamp"),
    )


class AbuseFlag(Base):
    """Abuse flag"""
    __tablename__ = "abuse_flags"

    flag_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flag_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    target_type = Column(String(50), nullable=False)
    target_id = Column(UUID(as_uuid=True), nullable=False)
    flagged_by = Column(String(50), default="system")
    flagged_by_id = Column(UUID(as_uuid=True))
    reason = Column(Text)
    evidence = Column(JSON)
    status = Column(String(20), default="PENDING")
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))
    reviewed_at = Column(DateTime)
    resolution = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index("idx_abuse_flags_target", "target_type", "target_id"),
        Index("idx_abuse_flags_status", "status", "severity"),
    )


class DailyMetric(Base):
    """Daily platform metrics"""
    __tablename__ = "daily_metrics"

    metric_date = Column(Date, primary_key=True)
    active_agents = Column(Integer)
    new_users = Column(Integer)
    tasks_created = Column(Integer)
    tasks_completed = Column(Integer)
    findings_discovered = Column(Integer)
    findings_verified = Column(Integer)
    findings_published = Column(Integer)
    findings_retracted = Column(Integer)
    total_amount_flagged = Column(Numeric(15, 2))
    average_confidence_score = Column(Numeric(3, 2))
    consensus_rate = Column(Numeric(3, 2))
    created_at = Column(DateTime, default=datetime.utcnow)
