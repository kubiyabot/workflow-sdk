"""
Runner service for managing Kubiya runners
"""
import logging
from typing import Dict, Any, List, Union

from kubiya_workflow_sdk.kubiya_services.constants import Endpoints
from kubiya_workflow_sdk.kubiya_services.exceptions import RunnerError
from kubiya_workflow_sdk.kubiya_services.services.base import BaseService

logger = logging.getLogger(__name__)


class RunnerService(BaseService):
    """Service for managing Kubiya runners"""

    def list(self) -> Union[List[Dict[str, Any]], str]:
        """
        List all runners with their health status.

        Returns:
            List of runner objects or formatted string based on output_format
        """
        # Use the v3 API endpoint directly
        endpoint = Endpoints.RUNNERS_LIST

        # Make the GET request
        runners = self._get(endpoint=endpoint).json()

        # Parse runners and convert version numbers to strings
        for raw_runner in runners:
            # Convert version from number to string if needed
            if isinstance(raw_runner.get('version'), (int, float)):
                if raw_runner['version'] == 0:
                    raw_runner['version'] = 'v1'
                elif raw_runner['version'] == 2:
                    raw_runner['version'] = 'v2'

        # Fetch health status for each runner concurrently
        runners = self._fetch_health_status_batch(runners)

        # Handle empty health status fields
        for runner in runners:
            for key in ['runner_health', 'tool_manager_health', 'agent_manager_health']:
                runner.setdefault(key, {}).setdefault('status', 'unknown')
                runner[key].setdefault('health', 'unknown')

            # Use kubernetes_namespace if namespace is empty
            if not runner.get('namespace') and runner.get('kubernetes_namespace'):
                runner['namespace'] = runner['kubernetes_namespace']

        return runners

    def manifest(
        self,
        name: str
    ) -> Dict[str, Any]:
        """
        Get runner's Kubernetes manifest

        Args:
            name: Runner name

        Returns:
            Dictionary containing manifest URL

        Raises:
            RunnerError: If manifest creation fails
        """
        # Use the formatted endpoint
        endpoint = self._format_endpoint(Endpoints.RUNNER_MANIFEST, runner_name=name)

        try:
            response = self._post(endpoint=endpoint, data=None)

            # Handle response format
            if hasattr(response, 'json'):
                try:
                    manifest = response.json()
                except:
                    raise RunnerError(f"Failed to parse response: {response.text}")
            else:
                manifest = response

            if not manifest.get('url'):
                raise RunnerError(f"Invalid manifest response: missing URL")

            return manifest
        except Exception as e:
            raise RunnerError(f"Failed to create runner manifest: {str(e)}")


    def _fetch_health_status_batch(
        self,
        runners: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Fetch health status for multiple runners concurrently.

        Args:
            runners: List of runner objects

        Returns:
            List of runners with updated health status
        """
        import concurrent.futures

        def fetch_health(runner):
            """Fetch health status for a single runner"""
            try:
                # Use the formatted endpoint for health check
                endpoint = self._format_endpoint(Endpoints.RUNNER_HEALTH, runner_name=runner.get('name'))
                response = self._get(endpoint=endpoint)

                # Handle response format
                if hasattr(response, 'json'):
                    try:
                        health_data = response.json()
                    except:
                        # If parsing fails, skip updating health
                        return runner
                else:
                    health_data = response

                # Initialize runner_health if not exists
                if 'runner_health' not in runner:
                    runner['runner_health'] = {}

                # Update runner health information
                runner['runner_health']['status'] = health_data.get('status', 'unknown')
                runner['runner_health']['health'] = health_data.get('health', 'unknown')
                runner['runner_health']['version'] = health_data.get('version', '')

                # Update tool manager health from checks
                for check in health_data.get('checks', []):
                    if check.get('name') == 'tool-manager':
                        runner['tool_manager_health'] = {
                            'status': check.get('status'),
                            'version': check.get('version'),
                            'error': check.get('error', '')
                        }
                    elif check.get('name') == 'agent-manager':
                        runner['agent_manager_health'] = {
                            'status': check.get('status'),
                            'version': check.get('version'),
                            'error': check.get('error', '')
                        }
            except Exception:
                # Silently fail, health status will remain as unknown
                pass

            return runner

        # Use ThreadPoolExecutor for concurrent health checks
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            # Submit all health check tasks
            future_to_runner = {
                executor.submit(fetch_health, runner): runner
                for runner in runners
            }

            # Collect results
            updated_runners = []
            for future in concurrent.futures.as_completed(future_to_runner):
                try:
                    updated_runner = future.result()
                    updated_runners.append(updated_runner)
                except Exception:
                    # If health check fails, keep the original runner
                    updated_runners.append(future_to_runner[future])

        return updated_runners
