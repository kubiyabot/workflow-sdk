"""
Webhook service for managing webhooks
"""
import json
import logging
from typing import Optional, Dict, Any, Union, List
from .base import BaseService
from ..constants import Endpoints
from ..exceptions import WebhookError, ValidationError

from ... import capture_exception

logger = logging.getLogger(__name__)


class WebhookService(BaseService):
    """Service for managing webhooks"""

    def list(
        self,
        limit: Optional[int] = None,
        output_format: str = "json"
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        List all webhooks

        Args:
            limit: Limit the number of webhooks to display
            output_format: Output format (json, yaml, text, wide)

        Returns:
            List of webhooks or formatted response
        """
        try:
            endpoint = self._format_endpoint(Endpoints.WEBHOOK_LIST)
            response = self._get(endpoint=endpoint).json()

            webhooks = response if isinstance(response, list) else response.get("webhooks", [])

            # Apply limit if specified
            if limit and 0 < limit < len(webhooks):
                webhooks = webhooks[:limit]

            return self._format_webhook_list(webhooks, output_format)

        except Exception as e:
            error = WebhookError(f"Failed to list webhooks: {str(e)}")
            capture_exception(error)
            raise error

    def get(self, webhook_id: str) -> Dict[str, Any]:
        """
        Get a specific webhook by ID

        Args:
            webhook_id: The webhook ID

        Returns:
            Webhook details
        """
        try:
            endpoint = self._format_endpoint(Endpoints.WEBHOOK_GET, webhook_id=webhook_id)
            return self._get(endpoint=endpoint).json()

        except Exception as e:
            error = WebhookError(f"Failed to get webhook {webhook_id}: {str(e)}")
            capture_exception(error)
            raise error

    def create(
        self,
        name: str,
        source: str,
        agent_id: Optional[str] = None,
        target: str = "agent",
        workflow: Optional[str] = None,
        runner: Optional[str] = None,
        method: str = "Slack",
        destination: Optional[str] = None,
        filter: Optional[str] = None,
        prompt: Optional[str] = None,
        hide_webhook_headers: bool = False,
    ) -> Dict[str, Any]:
        """
        Create a new webhook

        Args:
            name: Webhook name
            source: Event source (e.g., github, slack, custom)
            agent_id: Agent ID (required for agent target)
            target: Webhook target (agent|workflow)
            workflow: Workflow definition (for workflow target)
            runner: Runner name for workflow execution
            method: Communication method (Slack|Teams|HTTP)
            destination: Communication destination
            filter: Event filter (JMESPath expression)
            prompt: Agent prompt with template variables
            hide_webhook_headers: Hide webhook headers in notifications

        Returns:
            Created webhook details
        """
        try:

            # Validate required parameters
            if target == "agent" and not agent_id:
                raise ValidationError("agent_id is required for agent target")
            if target == "agent" and not prompt:
                raise ValidationError("prompt is required for agent target")
            if target == "workflow" and not workflow:
                raise ValidationError("workflow definition is required for workflow target")

            # Build webhook payload
            webhook_payload = {
                "name": name,
                "source": source,
                "filter": filter or "",
                "hide_webhook_headers": hide_webhook_headers,
                "communication": {
                    "method": method,
                    "destination": destination or ""
                }
            }

            if target == "agent":
                webhook_payload["agent_id"] = agent_id
                webhook_payload["prompt"] = prompt
            elif target == "workflow":
                webhook_payload["workflow"] = workflow
                if runner:
                    webhook_payload["runner"] = runner
                if agent_id:  # For workflow webhooks created with inline agents
                    webhook_payload["agent_id"] = agent_id
                if prompt:
                    webhook_payload["prompt"] = prompt

            # Handle Teams-specific destination formatting
            if webhook_payload["communication"]["method"].lower() == "teams":
                destination = webhook_payload["communication"]["destination"]
                if destination and ":" in destination and not destination.startswith("#{"):
                    # Convert "team:channel" format to Teams API format
                    parts = destination.split(":", 1)
                    webhook_payload["communication"][
                        "destination"] = f'{{"team_name": "{parts[0]}", "channel_name": "{parts[1]}"}}'

            endpoint = self._format_endpoint(Endpoints.WEBHOOK_CREATE)
            response = self._post(endpoint=endpoint, data=webhook_payload, stream=False).json()

            return response

        except ValidationError:
            raise
        except Exception as e:
            error = WebhookError(f"Failed to create webhook: {str(e)}")
            capture_exception(error)
            raise error

    def update(
        self,
        webhook_id: str,
        name: Optional[str] = None,
        source: Optional[str] = None,
        agent_id: Optional[str] = None,
        method: Optional[str] = None,
        destination: Optional[str] = None,
        filter_expression: Optional[str] = None,
        prompt: Optional[str] = None,
        hide_headers: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Update an existing webhook

        Args:
            webhook_id: The webhook ID to update
            name: New webhook name
            source: New event source
            agent_id: New agent ID
            method: New communication method
            destination: New communication destination
            filter_expression: New event filter
            prompt: New agent prompt
            hide_headers: New hide headers setting

        Returns:
            Updated webhook details
        """
        try:
            # Get existing webhook
            existing = self.get(webhook_id)

            # Update fields if provided
            if name is not None:
                existing["name"] = name
            if source is not None:
                existing["source"] = source
            if agent_id is not None:
                existing["agent_id"] = agent_id
            if method is not None:
                existing["communication"]["method"] = method
            if destination is not None:
                existing["communication"]["destination"] = destination
            if filter_expression is not None:
                existing["filter"] = filter_expression
            if prompt is not None:
                existing["prompt"] = prompt
            if hide_headers is not None:
                existing["hide_webhook_headers"] = hide_headers

            # Handle Teams-specific destination formatting
            if existing["communication"]["method"].lower() == "teams":
                dest = existing["communication"]["destination"]
                if dest and ":" in dest and not dest.startswith("#{"):
                    parts = dest.split(":", 1)
                    existing["communication"][
                        "destination"] = f'{{"team_name": "{parts[0]}", "channel_name": "{parts[1]}"}}'

            endpoint = self._format_endpoint(Endpoints.WEBHOOK_UPDATE, webhook_id=webhook_id)
            response = self._put(endpoint=endpoint, data=existing)

            return response

        except Exception as e:
            error = WebhookError(f"Failed to update webhook {webhook_id}: {str(e)}")
            capture_exception(error)
            raise error

    def delete(self, webhook_id: str) -> Dict[str, Any]:
        """
        Delete a webhook

        Args:
            webhook_id: The webhook ID to delete

        Returns:
            Deletion result
        """
        try:
            endpoint = self._format_endpoint(Endpoints.WEBHOOK_DELETE, webhook_id=webhook_id)
            response = self._delete(endpoint=endpoint)

            return response

        except Exception as e:
            error = WebhookError(f"Failed to delete webhook {webhook_id}: {str(e)}")
            capture_exception(error)
            raise error

    def test(
            self,
            webhook_id: Optional[str] = None,
            webhook_url: Optional[str] = None,
            test_data: Optional[Dict[str, Any]] = None,
            wait_for_response: bool = False,
            auto_generate: bool = False
    ) -> Union[Dict[str, Any], str]:
        """
        Test a webhook

        Args:
            webhook_id: Webhook ID (alternative to webhook_url)
            webhook_url: Direct webhook URL
            test_data: JSON data to send
            wait_for_response: Wait for HTTP response
            auto_generate: Auto-generate test data based on template variables

        Returns:
            Test result or response
        """
        try:
            # Get webhook URL if ID is provided
            if webhook_id and not webhook_url:
                webhook = self.get(webhook_id)
                webhook_url = webhook.get("webhook_url")

                if auto_generate and not test_data:
                    # Generate test data based on template variables
                    test_data = self._generate_test_data(webhook.get("prompt", ""))

            if not webhook_url:
                raise ValidationError("Either webhook_id or webhook_url must be provided")

            # Use default test data if none provided
            if not test_data:
                test_data = {
                    "test": True,
                    "timestamp": "2024-01-01T00:00:00Z",
                    "message": "Test webhook from Kubiya Python SDK"
                }

            # Convert dot notation to nested objects if needed
            test_data = self._convert_dot_notation_to_nested(test_data)

            endpoint = self._format_endpoint(Endpoints.WEBHOOK_TEST)

            # Prepare test request
            test_payload = {
                "webhook_url": webhook_url,
                "test_data": test_data,
                "wait_for_response": wait_for_response
            }

            response = self._post(endpoint=endpoint, data=test_payload, stream=False)

            return response

        except ValidationError:
            raise
        except Exception as e:
            error = WebhookError(f"Failed to test webhook: {str(e)}")
            capture_exception(error)
            raise error

    def import_from_file(self, file_path: str) -> Dict[str, Any]:
        """
        Import webhook from JSON/YAML file

        Args:
            file_path: Path to the webhook definition file

        Returns:
            Imported webhook details
        """
        try:
            import os
            import yaml

            if not os.path.exists(file_path):
                raise ValidationError(f"File not found: {file_path}")

            with open(file_path, 'r') as f:
                content = f.read()

            # Determine format and parse
            if file_path.lower().endswith(('.yaml', '.yml')):
                webhook_data = yaml.safe_load(content)
            else:
                webhook_data = json.loads(content)

            # Clear server-assigned fields
            webhook_data.pop("id", None)
            webhook_data.pop("created_at", None)
            webhook_data.pop("updated_at", None)
            webhook_data.pop("webhook_url", None)

            webhook_data = {
              "name": "GitHub PR Webhook",
              "source": "github",
              "agent_id": "abc-123-def-456",
              "filter": "event.action == 'opened'",
              "prompt": "New PR opened:\n- Title: {{.event.pull_request.title}}\n- Author: {{.event.pull_request.user.login}}\n- Repository: {{.event.repository.name}}",
              "hide_webhook_headers": False,
              "communication": {
                "method": "Slack",
                "destination": "#dev-notifications"
              }
            }
            webhook_data.update(**webhook_data.pop("communication", {}) or {})

            return self.create(**webhook_data,)

        except ValidationError:
            raise
        except Exception as e:
            error = WebhookError(f"Failed to import webhook from {file_path}: {str(e)}")
            capture_exception(error)
            raise error

    def export_to_file(
            self,
            webhook_id: str,
            file_path: str,
            format: str = "json"
    ) -> Dict[str, Any]:
        """
        Export webhook to JSON/YAML file

        Args:
            webhook_id: The webhook ID to export
            file_path: Output file path
            format: Export format (json|yaml)

        Returns:
            Export result
        """
        try:
            import yaml

            webhook = self.get(webhook_id)

            # Remove server-specific fields for export
            export_data = webhook.copy()
            export_data.pop("id", None)
            export_data.pop("created_at", None)
            export_data.pop("updated_at", None)
            export_data.pop("webhook_url", None)
            export_data.pop("org", None)

            # Write to file
            with open(file_path, 'w') as f:
                if format.lower() == "yaml":
                    yaml.dump(export_data, f, default_flow_style=False, indent=2)
                else:
                    json.dump(export_data, f, indent=2)

            return {
                "success": True,
                "file_path": file_path,
                "format": format,
                "webhook_name": webhook.get("name", "unknown")
            }

        except Exception as e:
            error = WebhookError(f"Failed to export webhook {webhook_id}: {str(e)}")
            capture_exception(error)
            raise error

    def get_template(self, format: str = "json") -> str:
        """
        Generate a webhook template

        Args:
            format: Template format (json|yaml)

        Returns:
            Template string
        """
        template_data = {
            "name": "example-webhook",
            "source": "github",
            "agent_id": "AGENT_ID_HERE",
            "hide_webhook_headers": False,
            "communication": {
                "method": "Slack",
                "destination": "#channel-name"
            },
            "filter": "pull_request[?state == 'open']",
            "prompt": "# GitHub Pull Request\n\nPlease analyze the following PR details:\n\n- Title: {{.event.pull_request.title}}\n- Author: {{.event.pull_request.user.login}}\n- Description: {{.event.pull_request.body}}"
        }

        if format.lower() == "yaml":
            import yaml
            return yaml.dump(template_data, default_flow_style=False, indent=2)
        else:
            return json.dumps(template_data, indent=2)

    def _generate_test_data(self, prompt: str) -> Dict[str, Any]:
        """
        Generate test data based on template variables in prompt

        Args:
            prompt: The webhook prompt containing template variables

        Returns:
            Generated test data
        """
        import re

        # Extract template variables like {{.event.field}}
        var_pattern = r'{{\s*\.([^{}]+)\s*}}'
        matches = re.findall(var_pattern, prompt)

        test_data = {}

        for var_path in matches:
            if var_path == "event":
                continue

            # Create nested structure for dot notation variables
            parts = var_path.split(".")
            current = test_data

            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    current[part] = f"sample-{part}"
                else:
                    if part not in current:
                        current[part] = {}
                    current = current[part]

        # Add default test metadata
        if not test_data:
            test_data = {
                "test": True,
                "timestamp": "2024-01-01T00:00:00Z",
                "message": "Auto-generated test webhook data"
            }
        else:
            test_data["_test"] = {
                "timestamp": "2024-01-01T00:00:00Z",
                "message": "Auto-generated test webhook data"
            }

        return test_data

    def _convert_dot_notation_to_nested(self, flat_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert flat keys with dots to nested objects

        Args:
            flat_data: Dictionary with potentially dot-notation keys

        Returns:
            Nested dictionary structure
        """
        result = {}

        for key, value in flat_data.items():
            if "." not in key:
                result[key] = value
                continue

            parts = key.split(".")
            current = result

            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    current[part] = value
                else:
                    if part not in current:
                        current[part] = {}
                    elif not isinstance(current[part], dict):
                        # Handle conflict by preserving old value
                        old_value = current[part]
                        current[part] = {"_value": old_value}
                    current = current[part]

        return result

    def create_workflow_webhook(
            self,
            name: str,
            source: str,
            workflow_definition: Union[str, Dict[str, Any]],
            runner: str = "kubiya-hosted",
            method: str = "Slack",
            destination: Optional[str] = None,
            filter_expression: Optional[str] = None,
            hide_headers: bool = False
    ) -> Dict[str, Any]:
        """
        Create a workflow webhook with automatic inline agent creation

        Args:
            name: Webhook name
            source: Event source
            workflow_definition: Workflow definition (JSON string, dict, or file/URL path)
            runner: Runner name for workflow execution
            method: Communication method
            destination: Communication destination
            filter_expression: Event filter
            hide_headers: Hide webhook headers

        Returns:
            Created webhook details
        """
        try:
            # Load workflow definition if it's a file path or URL
            if isinstance(workflow_definition, str):
                if workflow_definition.startswith(("file://", "http://", "https://")):
                    workflow_definition = self._load_workflow_definition(workflow_definition)
                else:
                    # Assume it's a JSON string
                    workflow_definition = json.loads(workflow_definition)

            # Create workflow webhook using the create method with workflow target
            return self.create(
                name=name,
                source=source,
                target="workflow",
                workflow=json.dumps(workflow_definition),
                runner=runner,
                method=method,
                destination=destination,
                filter=filter_expression,
                hide_webhook_headers=hide_headers
            )

        except Exception as e:
            error = WebhookError(f"Failed to create workflow webhook: {str(e)}")
            capture_exception(error)
            raise error

    def _load_workflow_definition(self, definition_path: str) -> Dict[str, Any]:
        """
        Load workflow definition from file or URL

        Args:
            definition_path: File path (file://) or URL (http(s)://)

        Returns:
            Parsed workflow definition
        """
        import os
        import requests
        import yaml

        if definition_path.startswith("file://"):
            file_path = definition_path[7:]  # Remove file:// prefix
            if not os.path.exists(file_path):
                raise ValidationError(f"Workflow file not found: {file_path}")

            with open(file_path, 'r') as f:
                content = f.read()

        elif definition_path.startswith(("http://", "https://")):
            response = requests.get(definition_path)
            response.raise_for_status()
            content = response.text

        else:
            raise ValidationError(f"Invalid workflow definition path: {definition_path}")

        # Parse YAML or JSON
        try:
            return yaml.safe_load(content)
        except yaml.YAMLError:
            return json.loads(content)

    def _format_webhook_list(self, webhooks: List[Dict[str, Any]], output_format: str) -> Union[
        List[Dict[str, Any]], Dict[str, Any], str]:
        """
        Format webhook list according to the specified output format

        Args:
            webhooks: List of webhook dictionaries
            output_format: Output format (json, yaml, text, wide)

        Returns:
            Formatted webhook list
        """
        if output_format == "json":
            return webhooks

        elif output_format == "yaml":
            import yaml
            return yaml.dump(webhooks, default_flow_style=False, indent=2)

        elif output_format == "wide":
            return self._format_webhooks_wide(webhooks)

        elif output_format == "text":
            return self._format_webhooks_text(webhooks)

        else:
            # Default to json for unknown formats
            return webhooks

    def _format_webhooks_text(self, webhooks: List[Dict[str, Any]]) -> str:
        """
        Format webhooks in default text/tabular format

        Args:
            webhooks: List of webhook dictionaries

        Returns:
            Formatted text string
        """
        if not webhooks:
            return "No webhooks found."

        # Create header
        output = []
        output.append("╭" + "─" * 88 + "╮")
        output.append("│ 🔗 WEBHOOKS" + " " * 75 + "│")
        output.append("╰" + "─" * 88 + "╯")
        output.append("")

        # Create table headers
        headers = ["ID", "NAME", "SOURCE", "DESTINATION", "METHOD"]
        separators = ["─" * 29, "─" * 23, "─" * 10, "─" * 23, "─" * 10]

        output.append(f" {headers[0]:<29} {headers[1]:<23} {headers[2]:<10} {headers[3]:<23} {headers[4]:<10}")
        output.append(f" {separators[0]} {separators[1]} {separators[2]} {separators[3]} {separators[4]}")

        # Add webhook rows
        for webhook in webhooks:
            webhook_id = self._truncate_string(webhook.get("id", ""), 29)
            name = self._truncate_string(webhook.get("name", ""), 23)
            source = self._truncate_string(webhook.get("source", ""), 10)

            comm = webhook.get("communication", {})
            method = comm.get("method", "")
            destination = self._format_destination_for_display(comm.get("destination", ""), method, 23)
            method_display = self._get_method_display(method)

            output.append(f" {webhook_id:<29} {name:<23} {source:<10} {destination:<23} {method_display:<10}")

        output.append("")
        output.append("💡 Tips:")
        output.append(f"  • Use webhook_service.get('<id>') to see detailed information")
        output.append(f"  • Use output_format='wide' to see additional fields")
        output.append(f"  • Use output_format='yaml' for machine-readable output")

        if len(webhooks) > 10:
            output.append(f"  • Use limit parameter to limit the displayed results")

        return "\n".join(output)

    def _format_webhooks_wide(self, webhooks: List[Dict[str, Any]]) -> str:
        """
        Format webhooks in wide/detailed format

        Args:
            webhooks: List of webhook dictionaries

        Returns:
            Formatted text string with detailed information
        """
        if not webhooks:
            return "No webhooks found."

        # Create header
        output = []
        output.append("╭" + "─" * 130 + "╮")
        output.append("│ 🔗 WEBHOOKS - DETAILED VIEW" + " " * 100 + "│")
        output.append("╰" + "─" * 130 + "╯")
        output.append("")

        # Create detailed table headers
        headers = ["ID", "NAME", "TYPE", "SOURCE", "DESTINATION", "METHOD", "FILTER", "CREATED BY", "MANAGED BY"]
        separators = ["─" * 31, "─" * 23, "─" * 11, "─" * 11, "─" * 23, "─" * 11, "─" * 11, "─" * 11, "─" * 11]

        header_line = f" {headers[0]:<31} {headers[1]:<23} {headers[2]:<11} {headers[3]:<11} {headers[4]:<23} {headers[5]:<11} {headers[6]:<11} {headers[7]:<11} {headers[8]:<11}"
        separator_line = f" {separators[0]} {separators[1]} {separators[2]} {separators[3]} {separators[4]} {separators[5]} {separators[6]} {separators[7]} {separators[8]}"

        output.append(header_line)
        output.append(separator_line)

        # Add webhook rows
        for webhook in webhooks:
            webhook_id = self._truncate_string(webhook.get("id", ""), 31)
            name = self._truncate_string(webhook.get("name", ""), 23)

            # Determine webhook type
            webhook_type = "🤖 Agent"
            if webhook.get("workflow"):
                webhook_type = "📋 Workflow"

            source = self._truncate_string(webhook.get("source", ""), 11)

            comm = webhook.get("communication", {})
            method = comm.get("method", "")
            destination = self._format_destination_for_display(comm.get("destination", ""), method, 23)
            method_display = self._get_method_display(method)

            filter_text = self._truncate_string(webhook.get("filter", "") or "<none>", 11)
            created_by = self._truncate_string(webhook.get("created_by", "") or "<none>", 11)
            managed_by = self._truncate_string(webhook.get("managed_by", "") or "<none>", 11)

            row = f" {webhook_id:<31} {name:<23} {webhook_type:<11} {source:<11} {destination:<23} {method_display:<11} {filter_text:<11} {created_by:<11} {managed_by:<11}"
            output.append(row)

        output.append("")
        output.append("💡 Tips:")
        output.append(f"  • Use webhook_service.get('<id>') to see detailed information")
        output.append(f"  • Use output_format='json' or 'yaml' for machine-readable output")

        return "\n".join(output)

    def _truncate_string(self, s: str, max_len: int) -> str:
        """Truncate string to max length with ellipsis"""
        if len(s) <= max_len:
            return s
        return s[:max_len - 3] + "..."

    def _format_destination_for_display(self, destination: str, method: str, max_len: int) -> str:
        """Format destination for display based on method type"""
        if not destination:
            return "<none>"

        if method.lower() == "teams":
            if destination.startswith("#{") and destination.endswith("}"):
                # Parse Teams JSON format
                try:
                    import json
                    teams_config = json.loads(destination[1:])  # Remove leading #
                    team_name = teams_config.get("team_name", "")
                    channel_name = teams_config.get("channel_name", "")
                    if team_name and channel_name:
                        formatted = f"{team_name}:{channel_name}"
                        return self._truncate_string(formatted, max_len)
                except:
                    pass
        elif method.lower() == "http" and not destination:
            return "HTTP SSE Stream"

        return self._truncate_string(destination, max_len)

    def _get_method_display(self, method: str) -> str:
        """Get display name for communication method"""
        if not method:
            return ""

        method_icons = {
            "slack": "💬 Slack",
            "teams": "👥 Teams",
            "http": "🌐 HTTP"
        }

        return method_icons.get(method.lower(), method)