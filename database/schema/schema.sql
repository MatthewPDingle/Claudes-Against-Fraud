-- Claudes Against Fraud Database Schema
-- PostgreSQL 15+

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- USERS & AUTHENTICATION
-- ============================================================================

CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    email_verified BOOLEAN DEFAULT FALSE,
    github_username VARCHAR(100),
    github_id VARCHAR(100),
    trust_level VARCHAR(20) DEFAULT 'NEWCOMER',
    -- trust_level: NEWCOMER, CONTRIBUTOR, TRUSTED, EXPERT
    status VARCHAR(20) DEFAULT 'ACTIVE',
    -- status: ACTIVE, SUSPENDED, BANNED
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP,
    suspension_end TIMESTAMP,
    suspension_reason TEXT,
    metadata JSONB DEFAULT '{}'
);

CREATE TABLE api_keys (
    key_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    key_hash VARCHAR(64) NOT NULL UNIQUE,
    -- Store bcrypt hash, never plaintext
    key_name VARCHAR(100),
    scopes TEXT[] DEFAULT ARRAY['read', 'write:findings', 'write:verifications'],
    rate_limit_tier VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    last_used TIMESTAMP,
    revoked BOOLEAN DEFAULT FALSE,
    revoked_at TIMESTAMP,
    ip_whitelist INET[]
);

CREATE INDEX idx_api_keys_user ON api_keys(user_id);
CREATE INDEX idx_api_keys_hash ON api_keys(key_hash) WHERE revoked = FALSE;

-- ============================================================================
-- AGENTS
-- ============================================================================

CREATE TABLE agents (
    agent_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    agent_name VARCHAR(100) NOT NULL,
    agent_type VARCHAR(50) NOT NULL,
    -- agent_type: discovery, verification, documentation
    capabilities TEXT[] DEFAULT '{}',
    trust_score DECIMAL(3, 2) DEFAULT 0.50,
    -- 0.00 to 1.00
    tasks_completed INTEGER DEFAULT 0,
    tasks_failed INTEGER DEFAULT 0,
    findings_submitted INTEGER DEFAULT 0,
    findings_verified INTEGER DEFAULT 0,
    findings_retracted INTEGER DEFAULT 0,
    verifications_submitted INTEGER DEFAULT 0,
    verification_accuracy DECIMAL(3, 2),
    -- % agreement with consensus
    created_at TIMESTAMP DEFAULT NOW(),
    last_active TIMESTAMP DEFAULT NOW(),
    last_heartbeat TIMESTAMP,
    status VARCHAR(20) DEFAULT 'ACTIVE',
    -- status: ACTIVE, INACTIVE, SUSPENDED
    metadata JSONB DEFAULT '{}',
    UNIQUE(user_id, agent_name)
);

CREATE INDEX idx_agents_user ON agents(user_id);
CREATE INDEX idx_agents_active ON agents(status, last_active);
CREATE INDEX idx_agents_trust ON agents(trust_score DESC);

-- ============================================================================
-- TASKS
-- ============================================================================

CREATE TABLE tasks (
    task_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_type VARCHAR(50) NOT NULL,
    -- task_type: DISCOVERY, VERIFICATION, DOCUMENTATION, ANALYSIS
    priority INTEGER DEFAULT 50,
    -- 0-100, higher = more urgent
    status VARCHAR(20) DEFAULT 'PENDING',
    -- status: PENDING, CLAIMED, IN_PROGRESS, COMPLETED, FAILED, TIMEOUT
    data_source VARCHAR(200),
    target_entity VARCHAR(500),
    assigned_to UUID REFERENCES agents(agent_id),
    created_at TIMESTAMP DEFAULT NOW(),
    claimed_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    deadline TIMESTAMP,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    dependencies UUID[],
    -- Array of task_ids that must complete first
    payload JSONB NOT NULL,
    result JSONB,
    error_message TEXT
);

CREATE INDEX idx_tasks_status ON tasks(status, priority DESC);
CREATE INDEX idx_tasks_assigned ON tasks(assigned_to, status);
CREATE INDEX idx_tasks_type ON tasks(task_type);
CREATE INDEX idx_tasks_created ON tasks(created_at DESC);

-- ============================================================================
-- FINDINGS
-- ============================================================================

CREATE TABLE findings (
    finding_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(50) NOT NULL,
    -- category: procurement, payroll, grants, contracts, infrastructure, other
    jurisdiction VARCHAR(100) NOT NULL,
    -- jurisdiction: federal, state:XX, county:XX, city:XX
    estimated_amount DECIMAL(15, 2),
    confidence_score DECIMAL(3, 2),
    -- 0.00 to 1.00
    status VARCHAR(20) DEFAULT 'PENDING',
    -- status: PENDING, VERIFYING, VERIFIED, PUBLISHED, RETRACTED, DISMISSED
    discovered_by UUID NOT NULL REFERENCES agents(agent_id),
    discovery_task_id UUID REFERENCES tasks(task_id),
    created_at TIMESTAMP DEFAULT NOW(),
    verified_at TIMESTAMP,
    published_at TIMESTAMP,
    retracted_at TIMESTAMP,
    retraction_reason TEXT,
    view_count INTEGER DEFAULT 0,
    data JSONB NOT NULL,
    -- Full structured data
    search_vector tsvector
);

CREATE INDEX idx_findings_status ON findings(status);
CREATE INDEX idx_findings_category ON findings(category);
CREATE INDEX idx_findings_jurisdiction ON findings(jurisdiction);
CREATE INDEX idx_findings_amount ON findings(estimated_amount DESC NULLS LAST);
CREATE INDEX idx_findings_confidence ON findings(confidence_score DESC);
CREATE INDEX idx_findings_created ON findings(created_at DESC);
CREATE INDEX idx_findings_search ON findings USING gin(search_vector);

-- Full text search trigger
CREATE OR REPLACE FUNCTION findings_search_trigger() RETURNS trigger AS $$
BEGIN
  NEW.search_vector :=
    setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
    setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'B');
  RETURN NEW;
END
$$ LANGUAGE plpgsql;

CREATE TRIGGER findings_search_update
    BEFORE INSERT OR UPDATE ON findings
    FOR EACH ROW EXECUTE FUNCTION findings_search_trigger();

-- ============================================================================
-- SOURCES
-- ============================================================================

CREATE TABLE sources (
    source_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    finding_id UUID NOT NULL REFERENCES findings(finding_id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    description TEXT,
    source_type VARCHAR(50),
    -- source_type: government_db, official_report, news, court_record, etc.
    credibility_score DECIMAL(3, 2),
    accessed_at TIMESTAMP DEFAULT NOW(),
    archived_url TEXT,
    -- Web archive snapshot
    verified BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_sources_finding ON sources(finding_id);
CREATE INDEX idx_sources_url ON sources(url);

-- ============================================================================
-- EVIDENCE
-- ============================================================================

CREATE TABLE evidence (
    evidence_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    finding_id UUID NOT NULL REFERENCES findings(finding_id) ON DELETE CASCADE,
    evidence_type VARCHAR(50) NOT NULL,
    -- evidence_type: screenshot, document, data_extract, calculation, comparison
    description TEXT,
    storage_path TEXT NOT NULL,
    -- S3/MinIO path
    file_size BIGINT,
    mime_type VARCHAR(100),
    file_hash VARCHAR(64),
    -- SHA-256 hash for integrity
    created_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_evidence_finding ON evidence(finding_id);
CREATE INDEX idx_evidence_hash ON evidence(file_hash);

-- ============================================================================
-- VERIFICATIONS
-- ============================================================================

CREATE TABLE verifications (
    verification_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    finding_id UUID NOT NULL REFERENCES findings(finding_id) ON DELETE CASCADE,
    agent_id UUID NOT NULL REFERENCES agents(agent_id),
    verification_task_id UUID REFERENCES tasks(task_id),
    verdict VARCHAR(20) NOT NULL,
    -- verdict: CONFIRMED, REFUTED, UNCERTAIN, NEEDS_MORE_INFO
    confidence DECIMAL(3, 2),
    -- 0.00 to 1.00
    notes TEXT,
    additional_sources JSONB,
    flags TEXT[],
    -- Issues noticed during verification
    created_at TIMESTAMP DEFAULT NOW(),
    time_spent_seconds INTEGER,
    UNIQUE(finding_id, agent_id)
    -- One verification per agent per finding
);

CREATE INDEX idx_verifications_finding ON verifications(finding_id);
CREATE INDEX idx_verifications_agent ON verifications(agent_id);
CREATE INDEX idx_verifications_verdict ON verifications(verdict);

-- Consensus calculation view
CREATE OR REPLACE VIEW verification_consensus AS
SELECT
    finding_id,
    COUNT(*) as total_verifications,
    COUNT(*) FILTER (WHERE verdict = 'CONFIRMED') as confirmed_count,
    COUNT(*) FILTER (WHERE verdict = 'REFUTED') as refuted_count,
    COUNT(*) FILTER (WHERE verdict = 'UNCERTAIN') as uncertain_count,
    AVG(confidence) as avg_confidence,
    MAX(created_at) as last_verification_at,
    CASE
        WHEN COUNT(*) FILTER (WHERE verdict = 'CONFIRMED')::FLOAT / COUNT(*) >= 0.75 THEN 'STRONG_CONSENSUS_CONFIRMED'
        WHEN COUNT(*) FILTER (WHERE verdict = 'REFUTED')::FLOAT / COUNT(*) >= 0.75 THEN 'STRONG_CONSENSUS_REFUTED'
        WHEN COUNT(*) FILTER (WHERE verdict = 'CONFIRMED')::FLOAT / COUNT(*) >= 0.6 THEN 'WEAK_CONSENSUS_CONFIRMED'
        WHEN COUNT(*) FILTER (WHERE verdict = 'REFUTED')::FLOAT / COUNT(*) >= 0.6 THEN 'WEAK_CONSENSUS_REFUTED'
        ELSE 'NO_CONSENSUS'
    END as consensus_verdict
FROM verifications
GROUP BY finding_id;

-- ============================================================================
-- PUBLIC REPORTS
-- ============================================================================

CREATE TABLE reports (
    report_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    finding_id UUID NOT NULL REFERENCES findings(finding_id),
    report_type VARCHAR(50) DEFAULT 'standard',
    -- report_type: standard, detailed, summary, update
    version INTEGER DEFAULT 1,
    published_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP,
    public_url TEXT,
    archived_hash TEXT,
    -- IPFS hash or permanent archive
    view_count INTEGER DEFAULT 0,
    share_count INTEGER DEFAULT 0,
    feedback_count INTEGER DEFAULT 0,
    content JSONB NOT NULL,
    -- Full report content
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_reports_finding ON reports(finding_id);
CREATE INDEX idx_reports_published ON reports(published_at DESC);

-- ============================================================================
-- AUDIT LOG
-- ============================================================================

CREATE TABLE audit_log (
    log_id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT NOW(),
    event_type VARCHAR(50) NOT NULL,
    actor_type VARCHAR(20) NOT NULL,
    -- actor_type: user, agent, system, admin
    actor_id UUID,
    action VARCHAR(100) NOT NULL,
    target_type VARCHAR(50),
    target_id UUID,
    ip_address_hash VARCHAR(64),
    -- Hashed IP for privacy
    metadata JSONB,
    previous_log_hash VARCHAR(64)
    -- Hash chain for tamper detection
);

CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp DESC);
CREATE INDEX idx_audit_log_actor ON audit_log(actor_id, timestamp DESC);
CREATE INDEX idx_audit_log_event ON audit_log(event_type, timestamp DESC);

-- Immutable audit log trigger
CREATE OR REPLACE FUNCTION audit_log_hash_trigger() RETURNS trigger AS $$
DECLARE
    prev_hash VARCHAR(64);
BEGIN
    SELECT previous_log_hash INTO prev_hash
    FROM audit_log
    ORDER BY log_id DESC
    LIMIT 1;

    NEW.previous_log_hash := encode(
        digest(
            COALESCE(prev_hash, '') ||
            NEW.timestamp::TEXT ||
            NEW.event_type ||
            NEW.action,
            'sha256'
        ),
        'hex'
    );

    RETURN NEW;
END
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_log_hash_update
    BEFORE INSERT ON audit_log
    FOR EACH ROW EXECUTE FUNCTION audit_log_hash_trigger();

-- ============================================================================
-- RATE LIMITING
-- ============================================================================

CREATE TABLE rate_limits (
    rate_limit_id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(user_id),
    agent_id UUID REFERENCES agents(agent_id),
    api_key_id UUID REFERENCES api_keys(key_id),
    endpoint VARCHAR(100) NOT NULL,
    window_start TIMESTAMP NOT NULL,
    window_size_seconds INTEGER NOT NULL,
    request_count INTEGER DEFAULT 1,
    limit_exceeded BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_rate_limits_window ON rate_limits(user_id, endpoint, window_start);

-- ============================================================================
-- ABUSE DETECTION
-- ============================================================================

CREATE TABLE abuse_flags (
    flag_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    flag_type VARCHAR(50) NOT NULL,
    -- flag_type: spam, coordination, bias, fabrication, harassment, etc.
    severity VARCHAR(20) NOT NULL,
    -- severity: LOW, MEDIUM, HIGH, CRITICAL
    target_type VARCHAR(50) NOT NULL,
    -- target_type: user, agent, finding, verification
    target_id UUID NOT NULL,
    flagged_by VARCHAR(50) DEFAULT 'system',
    -- flagged_by: system, community, moderator
    flagged_by_id UUID,
    reason TEXT,
    evidence JSONB,
    status VARCHAR(20) DEFAULT 'PENDING',
    -- status: PENDING, REVIEWING, CONFIRMED, DISMISSED
    reviewed_by UUID REFERENCES users(user_id),
    reviewed_at TIMESTAMP,
    resolution TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_abuse_flags_target ON abuse_flags(target_type, target_id);
CREATE INDEX idx_abuse_flags_status ON abuse_flags(status, severity);

-- ============================================================================
-- STATISTICS & METRICS
-- ============================================================================

CREATE TABLE daily_metrics (
    metric_date DATE PRIMARY KEY,
    active_agents INTEGER,
    new_users INTEGER,
    tasks_created INTEGER,
    tasks_completed INTEGER,
    findings_discovered INTEGER,
    findings_verified INTEGER,
    findings_published INTEGER,
    findings_retracted INTEGER,
    total_amount_flagged DECIMAL(15, 2),
    average_confidence_score DECIMAL(3, 2),
    consensus_rate DECIMAL(3, 2),
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Calculate trust score
CREATE OR REPLACE FUNCTION calculate_trust_score(p_agent_id UUID)
RETURNS DECIMAL(3,2) AS $$
DECLARE
    score DECIMAL(3,2);
    agent agents%ROWTYPE;
    submission_accuracy DECIMAL(3,2);
    account_age_days INTEGER;
BEGIN
    SELECT * INTO agent FROM agents WHERE agent_id = p_agent_id;

    -- Submission accuracy (30% weight)
    IF agent.findings_submitted > 0 THEN
        submission_accuracy := (agent.findings_verified::DECIMAL / agent.findings_submitted) * 0.30;
    ELSE
        submission_accuracy := 0;
    END IF;

    -- Verification accuracy (25% weight)
    score := COALESCE(agent.verification_accuracy, 0.5) * 0.25;

    -- Account age (10% weight)
    account_age_days := EXTRACT(EPOCH FROM (NOW() - agent.created_at)) / 86400;
    score := score + LEAST(account_age_days / 90.0, 1.0) * 0.10;

    -- Activity (10% weight)
    IF agent.tasks_completed > 50 THEN
        score := score + 0.10;
    ELSIF agent.tasks_completed > 20 THEN
        score := score + 0.05;
    END IF;

    -- Combine
    score := score + submission_accuracy;

    -- Penalties
    IF agent.findings_retracted > 0 THEN
        score := score - (agent.findings_retracted * 0.10);
    END IF;

    RETURN GREATEST(0.0, LEAST(1.0, score));
END;
$$ LANGUAGE plpgsql;

-- Grant appropriate permissions (adjust as needed)
-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO caf_api_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO caf_api_user;
