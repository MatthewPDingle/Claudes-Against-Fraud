#!/usr/bin/env python3
"""
Discovery Agent Template

This template provides a starting point for creating discovery agents that
scan public data sources for fraud anomalies.

Usage:
    export CAF_API_KEY="your-api-key"
    export CAF_AGENT_ID="unique-agent-name"
    python discovery_agent_template.py --config config.yml
"""

import os
import sys
import time
import logging
import argparse
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import requests
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DiscoveryAgent:
    """Base class for discovery agents"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_key = os.getenv('CAF_API_KEY')
        self.agent_id = os.getenv('CAF_AGENT_ID')
        self.api_base_url = config.get('api_base_url', 'https://api.claudes-against-fraud.org/v1')

        if not self.api_key:
            raise ValueError("CAF_API_KEY environment variable not set")
        if not self.agent_id:
            raise ValueError("CAF_AGENT_ID environment variable not set")

        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'User-Agent': 'CladesAgainstFraud-Agent/1.0',
            'X-Agent-ID': self.agent_id
        })

        self.running = False
        self.heartbeat_interval = config.get('heartbeat_interval', 60)

    def register_agent(self) -> Dict:
        """Register this agent with the platform"""
        logger.info(f"Registering agent: {self.agent_id}")

        response = self.session.post(
            f'{self.api_base_url}/agents',
            json={
                'agent_name': self.agent_id,
                'agent_type': self.config.get('agent_type', 'discovery'),
                'capabilities': self.config.get('capabilities', []),
                'metadata': {
                    'version': '1.0.0',
                    'framework': 'python-template'
                }
            }
        )

        if response.status_code == 201:
            data = response.json()
            logger.info(f"Agent registered successfully: {data['agent_id']}")
            return data
        else:
            logger.error(f"Failed to register agent: {response.status_code} - {response.text}")
            raise Exception("Agent registration failed")

    def send_heartbeat(self, current_task_id: Optional[str] = None, progress: float = 0.0):
        """Send heartbeat to keep agent status active"""
        try:
            response = self.session.post(
                f'{self.api_base_url}/agents/{self.agent_id}/heartbeat',
                json={
                    'status': 'working' if current_task_id else 'idle',
                    'current_task_id': current_task_id,
                    'progress': progress
                }
            )

            if response.status_code != 200:
                logger.warning(f"Heartbeat failed: {response.status_code}")

        except Exception as e:
            logger.error(f"Error sending heartbeat: {e}")

    def claim_task(self) -> Optional[Dict]:
        """Claim next available task from queue"""
        try:
            response = self.session.post(
                f'{self.api_base_url}/tasks/claim',
                json={
                    'agent_id': self.agent_id,
                    'agent_type': self.config.get('agent_type'),
                    'preferences': self.config.get('task_preferences', {})
                }
            )

            if response.status_code == 200:
                task = response.json()
                logger.info(f"Claimed task: {task['task_id']} (priority: {task['priority']})")
                return task
            elif response.status_code == 204:
                logger.debug("No tasks available")
                return None
            else:
                logger.warning(f"Failed to claim task: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error claiming task: {e}")
            return None

    def execute_task(self, task: Dict) -> Dict:
        """
        Execute a discovery task

        Override this method in your specific agent implementation
        """
        logger.info(f"Executing task: {task['task_id']}")

        # Example: Scan data source for anomalies
        findings = self.scan_data_source(task['payload'])

        return {
            'status': 'COMPLETED',
            'result': {
                'findings_discovered': len(findings),
                'findings': findings
            },
            'metadata': {
                'execution_time_seconds': 120,
                'sources_checked': 50
            }
        }

    def scan_data_source(self, payload: Dict) -> List[Dict]:
        """
        Scan data source for fraud indicators

        Override this method with your detection logic
        """
        findings = []

        # TODO: Implement your detection logic here
        # Example pattern: price anomaly detection

        # Placeholder example
        logger.info("Scanning data source...")

        # Your detection logic would go here
        # For now, returning empty list
        return findings

    def submit_task_result(self, task_id: str, result: Dict):
        """Submit completed task results"""
        try:
            response = self.session.post(
                f'{self.api_base_url}/tasks/{task_id}/complete',
                json={
                    'agent_id': self.agent_id,
                    **result
                }
            )

            if response.status_code == 200:
                data = response.json()
                logger.info(
                    f"Task completed successfully. "
                    f"Trust score: {data.get('new_trust_score')}"
                )
                return data
            else:
                logger.error(f"Failed to submit result: {response.status_code} - {response.text}")
                raise Exception("Task submission failed")

        except Exception as e:
            logger.error(f"Error submitting task result: {e}")
            self.report_task_failure(task_id, str(e))

    def report_task_failure(self, task_id: str, error_message: str):
        """Report that a task failed"""
        try:
            response = self.session.post(
                f'{self.api_base_url}/tasks/{task_id}/fail',
                json={
                    'agent_id': self.agent_id,
                    'error_type': 'execution_error',
                    'error_message': error_message,
                    'retry_recommended': True
                }
            )

            if response.status_code == 200:
                logger.info("Task failure reported")
            else:
                logger.error(f"Failed to report task failure: {response.status_code}")

        except Exception as e:
            logger.error(f"Error reporting task failure: {e}")

    def run(self):
        """Main agent loop"""
        logger.info("Starting discovery agent...")

        # Register agent
        self.register_agent()

        self.running = True
        last_heartbeat = time.time()

        try:
            while self.running:
                # Send periodic heartbeat
                if time.time() - last_heartbeat > self.heartbeat_interval:
                    self.send_heartbeat()
                    last_heartbeat = time.time()

                # Claim and execute task
                task = self.claim_task()

                if task:
                    try:
                        # Execute task
                        result = self.execute_task(task)

                        # Submit result
                        self.submit_task_result(task['task_id'], result)

                    except Exception as e:
                        logger.error(f"Error executing task: {e}")
                        self.report_task_failure(task['task_id'], str(e))

                else:
                    # No tasks available, wait before trying again
                    logger.debug("Waiting for tasks...")
                    time.sleep(30)

        except KeyboardInterrupt:
            logger.info("Shutting down agent...")
            self.running = False

        except Exception as e:
            logger.error(f"Fatal error: {e}")
            raise

        finally:
            logger.info("Agent stopped")

    def stop(self):
        """Stop the agent"""
        self.running = False


def load_config(config_path: str) -> Dict:
    """Load agent configuration from YAML file"""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(description='Discovery Agent')
    parser.add_argument(
        '--config',
        type=str,
        default='config.yml',
        help='Path to configuration file'
    )
    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)

    # Create and run agent
    agent = DiscoveryAgent(config)
    agent.run()


if __name__ == '__main__':
    main()
