"""
Datadog provider for trigger management
"""
import json
import os
import requests
from typing import Dict, Any, List, Optional

from kubiya_workflow_sdk.kubiya_services.exceptions import ProviderError, ValidationError

from kubiya_workflow_sdk import capture_exception



class DatadogProvider:
    """Datadog provider for managing webhook triggers"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        app_key: Optional[str] = None,
        site: Optional[str] = None
    ):
        """
        Initialize Datadog provider

        Args:
            api_key: Datadog API key
            app_key: Datadog application key
            site: Datadog site (optional)
        """
        self.api_key = api_key or os.getenv("DD_API_KEY")
        self.app_key = app_key or os.getenv("DD_APPLICATION_KEY")
        self.site = site or os.getenv("DD_SITE")

        if not self.api_key:
            raise ProviderError("DD_API_KEY environment variable or api_key parameter is required")
        if not self.app_key:
            raise ProviderError("DD_APPLICATION_KEY environment variable or app_key parameter is required")

        # Set base URL
        if self.site:
            self.base_url = f"https://{self.site}"
        else:
            self.base_url = "https://api.datadoghq.com"

        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
            "DD-API-KEY": self.api_key,
            "DD-APPLICATION-KEY": self.app_key
        })

    def create_trigger(self, trigger: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new Datadog webhook trigger

        Args:
            trigger: Trigger configuration

        Returns:
            Created trigger details
        """
        try:
            config = trigger.get("config", {})
            workflow_content = self._read_workflow_content(trigger["workflow_ref"])

            # Generate Kubiya webhook URL
            runner = self._get_runner_from_config(config)
            kubiya_webhook_url = f"https://api.kubiya.ai/api/v1/workflow?runner={runner}&operation=execute_workflow"

            # Prepare webhook payload
            webhook_payload = {
                "name": f"webhooks/{config['webhook_name']}",
                "url": kubiya_webhook_url,
                "encode_as": config.get("encode_as", "json"),
                "custom_headers": self._get_custom_headers(config, trigger, workflow_content),
                "payload": self._get_payload(config, workflow_content)
            }

            # Create webhook in Datadog
            url = f"{self.base_url}/api/v1/integration/webhooks"
            response = self.session.post(url, json=webhook_payload)
            response.raise_for_status()

            return {
                "success": True,
                "webhook_url": kubiya_webhook_url,
                "datadog_webhook": response.json() if response.content else {}
            }

        except requests.RequestException as e:
            error = ProviderError(f"Datadog API error: {str(e)}")
            capture_exception(error)
            raise error
        except Exception as e:
            error = ProviderError(f"Failed to create Datadog trigger: {str(e)}")
            capture_exception(error)
            raise error

    def update_trigger(self, trigger: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing Datadog webhook trigger

        Args:
            trigger: Updated trigger configuration

        Returns:
            Update result
        """
        # For Datadog, we can use the same logic as create since PUT is idempotent
        return self.create_trigger(trigger)

    def delete_trigger(self, webhook_name: str) -> Dict[str, Any]:
        """
        Delete a Datadog webhook trigger

        Args:
            webhook_name: Name of the webhook to delete

        Returns:
            Deletion result
        """
        try:
            url = f"{self.base_url}/api/v1/integration/webhooks/{webhook_name}"
            response = self.session.delete(url)
            response.raise_for_status()

            return {"success": True, "message": f"Webhook {webhook_name} deleted"}

        except requests.RequestException as e:
            error = ProviderError(f"Failed to delete Datadog webhook: {str(e)}")
            capture_exception(error)
            raise error

    def list_webhooks(self) -> List[Dict[str, Any]]:
        """
        List all Datadog webhooks and identify Kubiya ones

        Returns:
            List of webhook information
        """
        try:
            url = f"{self.base_url}/api/v1/integration/webhooks"
            response = self.session.get(url)
            response.raise_for_status()

            webhooks = response.json() if response.content else []
            webhook_info = []

            for webhook in webhooks:
                name = webhook.get("name", "")
                webhook_url = webhook.get("url", "")
                is_kubiya = "api.kubiya.ai" in webhook_url or "kubiya" in webhook_url

                webhook_info.append({
                    "name": name,
                    "url": webhook_url,
                    "provider": "datadog",
                    "is_kubiya": is_kubiya
                })

            return webhook_info

        except requests.RequestException as e:
            error = ProviderError(f"Failed to list Datadog webhooks: {str(e)}")
            capture_exception(error)
            raise error

    def test_trigger(self, trigger_id: str) -> Dict[str, Any]:
        """
        Test a Datadog webhook trigger

        Args:
            trigger_id: ID of the trigger to test

        Returns:
            Test result
        """
        # This would simulate a webhook call to test the integration
        raise NotImplementedError("Datadog trigger testing not yet implemented")

    def validate_config(self, config: Dict[str, Any]) -> None:
        """
        Validate Datadog-specific configuration

        Args:
            config: Configuration to validate

        Raises:
            ValidationError: If configuration is invalid
        """
        webhook_name = config.get("webhook_name")
        if not webhook_name:
            raise ValidationError("webhook_name is required")

        # Validate webhook name format
        if " " in webhook_name:
            raise ValidationError("webhook_name cannot contain spaces")

        # Validate encode_as if provided
        encode_as = config.get("encode_as", "json")
        if encode_as not in ["json", "form"]:
            raise ValidationError(f"Invalid encode_as value: {encode_as}")

    def get_required_env_vars(self) -> List[str]:
        """
        Get required environment variables

        Returns:
            List of required environment variable names
        """
        return ["DD_API_KEY", "DD_APPLICATION_KEY"]

    def _read_workflow_content(self, workflow_path: str) -> str:
        """Read workflow file content"""
        try:
            with open(workflow_path, 'r') as f:
                return f.read()
        except Exception as e:
            raise ProviderError(f"Failed to read workflow file {workflow_path}: {str(e)}")

    def _get_runner_from_config(self, config: Dict[str, Any]) -> str:
        """Get runner from config or use default"""
        environment = config.get("environment", {})
        if isinstance(environment, dict) and "KUBIYA_RUNNER" in environment:
            return environment["KUBIYA_RUNNER"]
        return os.getenv("KUBIYA_RUNNER", "gke-integration")

    def _get_custom_headers(
        self,
        config: Dict[str, Any],
        trigger: Dict[str, Any],
        workflow_content: str
    ) -> str:
        """Get custom headers for webhook"""
        custom_headers = config.get("custom_headers", "")
        if custom_headers:
            return custom_headers

        # Default headers
        return f"User-Agent: Datadog-Webhook-1.0\nContent-Type: application/yaml\nX-Trigger-ID: {trigger['id']}"

    def _get_payload(self, config: Dict[str, Any], workflow_content: str) -> str:
        """Get payload template for webhook"""
        payload = config.get("payload", "")
        if payload:
            return payload

        # Default payload that includes workflow content
        return json.dumps({
            "workflow": workflow_content,
            "event_data": {
                "body": "$EVENT_MSG",
                "title": "$EVENT_TITLE",
                "date": "$DATE",
                "id": "$ID",
                "priority": "$PRIORITY",
                "tags": "$TAGS"
            }
        })
