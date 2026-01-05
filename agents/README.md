# Agent Templates

This directory contains agent templates and workflows for contributors to run using their Claude subscriptions.

## Directory Structure

- **discovery/** - Discovery agents that scan for fraud anomalies
- **verification/** - Verification agents that cross-check findings
- **documentation/** - Documentation agents that compile reports
- **templates/** - Reusable agent templates and configurations

## Agent Types

### Discovery Agents
Autonomous agents that scan public data sources for anomalies:
- Price comparison analyzers
- Shell company detectors
- Conflict of interest mappers
- Timeline inconsistency finders

### Verification Agents
Agents that independently verify findings from other agents:
- Source validation
- Cross-referencing
- Mathematical validation
- Context assessment

### Documentation Agents
Agents that compile evidence and create public reports:
- Evidence packaging
- Report generation
- Visualization creation
- Citation formatting

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
export CAF_API_KEY="your-api-key"
export CAF_AGENT_ID="unique-agent-name"

# Run a discovery agent
python discovery/contract_scanner.py --source=usaspending --mode=autonomous

# Run a verification agent
python verification/consensus_verifier.py --mode=autonomous
```

## Configuration

Each agent uses a YAML configuration file:

```yaml
agent:
  type: discovery
  name: contract-scanner-ny
  version: 1.0

data_source:
  name: usaspending_gov
  filters:
    jurisdiction: NY
    category: contracts
    min_amount: 10000

detection:
  patterns:
    - price_anomaly
    - shell_company
    - conflict_of_interest
  confidence_threshold: 0.3

runtime:
  autonomous: true
  max_duration: 4h
  heartbeat_interval: 60s
```

## Development

To create a new agent:

1. Copy a template from `templates/`
2. Customize the configuration
3. Implement detection logic
4. Test locally
5. Submit for review

See [Contributing Guide](../CONTRIBUTING.md) for details.
