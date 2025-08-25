"""
GitHub provider for trigger management
"""
import os
import requests
from typing import Dict, Any, List, Optional
from kubiya_workflow_sdk.kubiya_services.exceptions import ProviderError, ValidationError

from kubiya_workflow_sdk import capture_exception



class GitHubProvider:
    """GitHub provider for managing webhook triggers"""

    def __init__(self, token: Optional[str] = None):
        """
        Initialize GitHub provider

        Args:
            token: GitHub personal access token
        """
        self.token = token or os.getenv("GITHUB_TOKEN")
        if not self.token:
            raise ProviderError("GITHUB_TOKEN environment variable or token parameter is required")

        self.base_url = "https://api.github.com"
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {self.token}",
            "Content-Type": "application/json"
        })

    def create_trigger(self, trigger: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new GitHub webhook trigger

        Args:
            trigger: Trigger configuration

        Returns:
            Created trigger details
        """
        try:
            config = trigger.get("config", {})
            repository = config["repository"]
            events = config.get("events", ["push"])
            secret = config.get("secret", "")

            # Parse repository
            owner, repo = self._parse_repository(repository)

            # Generate Kubiya webhook URL
            runner = self._get_runner_from_config(config)
            kubiya_webhook_url = f"https://api.kubiya.ai/api/v1/workflow?runner={runner}&operation=execute_workflow"

            # Prepare webhook payload
            webhook_payload = {
                "name": "web",
                "active": True,
                "events": events,
                "config": {
                    "url": kubiya_webhook_url,
                    "content_type": "json",
                    "insecure_ssl": "0"
                }
            }

            # Add secret if provided
            if secret:
                webhook_payload["config"]["secret"] = secret

            # Create webhook in GitHub
            url = f"{self.base_url}/repos/{owner}/{repo}/hooks"
            response = self.session.post(url, json=webhook_payload)
            response.raise_for_status()

            webhook_data = response.json() if response.content else {}
            return {
                "success": True,
                "webhook_url": kubiya_webhook_url,
                "github_webhook": webhook_data,
                "webhook_id": webhook_data.get("id")
            }

        except requests.RequestException as e:
            error = ProviderError(f"GitHub API error: {str(e)}")
            capture_exception(error)
            raise error
        except Exception as e:
            error = ProviderError(f"Failed to create GitHub trigger: {str(e)}")
            capture_exception(error)
            raise error

    def update_trigger(self, trigger: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing GitHub webhook trigger

        Args:
            trigger: Updated trigger configuration

        Returns:
            Update result
        """
        # GitHub webhooks need webhook ID to update
        raise NotImplementedError("GitHub webhook updates not yet implemented - please delete and recreate")

    def delete_trigger(self, repository: str, webhook_id: str) -> Dict[str, Any]:
        """
        Delete a GitHub webhook trigger

        Args:
            repository: Repository in format 'owner/repo'
            webhook_id: ID of the webhook to delete

        Returns:
            Deletion result
        """
        try:
            owner, repo = self._parse_repository(repository)
            url = f"{self.base_url}/repos/{owner}/{repo}/hooks/{webhook_id}"

            response = self.session.delete(url)
            response.raise_for_status()

            return {"success": True, "message": f"Webhook {webhook_id} deleted from {repository}"}

        except requests.RequestException as e:
            error = ProviderError(f"Failed to delete GitHub webhook: {str(e)}")
            capture_exception(error)
            raise error

    def list_webhooks(self, repository: str) -> List[Dict[str, Any]]:
        """
        List all GitHub webhooks for a repository

        Args:
            repository: Repository in format 'owner/repo'

        Returns:
            List of webhook information
        """
        try:
            owner, repo = self._parse_repository(repository)
            url = f"{self.base_url}/repos/{owner}/{repo}/hooks"

            response = self.session.get(url)
            response.raise_for_status()

            webhooks = response.json() if response.content else []
            webhook_info = []

            for webhook in webhooks:
                webhook_id = str(webhook.get("id", ""))
                name = webhook.get("name", "")

                config = webhook.get("config", {})
                webhook_url = config.get("url", "")

                events = webhook.get("events", [])
                is_kubiya = "api.kubiya.ai" in webhook_url or "kubiya" in webhook_url

                webhook_info.append({
                    "id": webhook_id,
                    "name": name,
                    "url": webhook_url,
                    "provider": "github",
                    "is_kubiya": is_kubiya,
                    "events": events
                })

            return webhook_info

        except requests.RequestException as e:
            error = ProviderError(f"Failed to list GitHub webhooks: {str(e)}")
            capture_exception(error)
            raise error

    def test_trigger(self, trigger_id: str) -> Dict[str, Any]:
        """
        Test a GitHub webhook trigger

        Args:
            trigger_id: ID of the trigger to test

        Returns:
            Test result
        """
        # GitHub has test webhook functionality that could be used
        raise NotImplementedError("GitHub trigger testing not yet implemented")

    def validate_config(self, config: Dict[str, Any]) -> None:
        """
        Validate GitHub-specific configuration

        Args:
            config: Configuration to validate

        Raises:
            ValidationError: If configuration is invalid
        """
        repository = config.get("repository")
        if not repository:
            raise ValidationError("repository is required")

        # Validate repository format
        try:
            self._parse_repository(repository)
        except ValueError as e:
            raise ValidationError(str(e))

        # Validate events
        events = config.get("events", [])
        if not events:
            raise ValidationError("at least one event is required")

        # Validate event names
        valid_events = {
            "push", "pull_request", "issues", "issue_comment",
            "pull_request_review", "pull_request_review_comment",
            "commit_comment", "create", "delete", "deployment",
            "deployment_status", "fork", "gollum", "label",
            "member", "membership", "milestone", "organization",
            "org_block", "page_build", "project", "project_card",
            "project_column", "public", "release", "repository",
            "status", "team", "team_add", "watch"
        }

        for event in events:
            if not isinstance(event, str):
                raise ValidationError(f"event must be a string, got: {type(event)}")
            if event not in valid_events:
                raise ValidationError(f"invalid event: {event}")

    def get_required_env_vars(self) -> List[str]:
        """
        Get required environment variables

        Returns:
            List of required environment variable names
        """
        return ["GITHUB_TOKEN"]

    def _parse_repository(self, repository: str) -> tuple:
        """
        Parse repository string into owner and repo

        Args:
            repository: Repository in format 'owner/repo'

        Returns:
            Tuple of (owner, repo)

        Raises:
            ValueError: If repository format is invalid
        """
        parts = repository.split("/")
        if len(parts) != 2:
            raise ValueError(f"repository must be in format 'owner/repo', got: {repository}")
        return parts[0], parts[1]

    def _get_runner_from_config(self, config: Dict[str, Any]) -> str:
        """Get runner from environment or use default"""
        return os.getenv("KUBIYA_RUNNER", "gke-integration")

    def _read_workflow_content(self, workflow_path: str) -> str:
        """Read workflow file content"""
        try:
            with open(workflow_path, 'r') as f:
                return f.read()
        except Exception as e:
            raise ProviderError(f"Failed to read workflow file {workflow_path}: {str(e)}")
