"""
Trigger service for managing workflow triggers
"""
import logging
import os
import time
from typing import Optional, Dict, Any, List
from kubiya_workflow_sdk.kubiya_services.services.base import BaseService
from kubiya_workflow_sdk.kubiya_services.exceptions import TriggerError, ValidationError

from kubiya_workflow_sdk import capture_exception

logger = logging.getLogger(__name__)


class TriggerService(BaseService):
    """Service for managing workflow triggers"""

    def create(
        self,
        provider: str,
        workflow_file: str,
        name: str,
        webhook_name: Optional[str] = None,
        custom_headers: Optional[str] = None,
        payload: Optional[str] = None,
        encode_as: str = "json",
        runner: Optional[str] = None,
        # Provider credentials (alternatives to env vars)
        dd_api_key: Optional[str] = None,
        dd_app_key: Optional[str] = None,
        dd_site: Optional[str] = None,
        github_token: Optional[str] = None,
        # GitHub specific
        repository: Optional[str] = None,
        events: Optional[List[str]] = None,
        secret: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new workflow trigger

        Args:
            provider: Provider type (datadog, github)
            workflow_file: Path to the workflow file
            name: Human-readable name for the trigger
            webhook_name: Name for the webhook in the external provider
            custom_headers: Custom headers for the webhook
            payload: Custom payload template for the webhook
            encode_as: Encoding format for the webhook payload
            runner: Runner to use for workflow execution
            dd_api_key: Datadog API key (alternative to DD_API_KEY env var)
            dd_app_key: Datadog application key (alternative to DD_APPLICATION_KEY env var)
            dd_site: Datadog site (alternative to DD_SITE env var)
            github_token: GitHub token (alternative to GITHUB_TOKEN env var)
            repository: GitHub repository in format 'owner/repo'
            events: GitHub events to trigger on
            secret: Webhook secret for GitHub verification

        Returns:
            Created trigger details
        """
        try:
            # Validate inputs
            if not provider:
                raise ValidationError("Provider is required")
            if not workflow_file:
                raise ValidationError("Workflow file is required")
            if not name:
                raise ValidationError("Name is required")

            provider = provider.lower()
            if provider not in ["datadog", "github"]:
                raise ValidationError(f"Unsupported provider: {provider} (supported: datadog, github)")

            # Provider-specific validation
            if provider == "github":
                if not repository:
                    raise ValidationError("Repository is required for GitHub provider")
                if not events or len(events) == 0:
                    raise ValidationError("Events are required for GitHub provider")

            # Validate workflow file exists
            if not os.path.isabs(workflow_file):
                workflow_file = os.path.abspath(workflow_file)

            if not os.path.exists(workflow_file):
                raise ValidationError(f"Workflow file does not exist: {workflow_file}")

            # Generate unique trigger ID
            import uuid
            trigger_id = str(uuid.uuid4())

            # Use name as webhook name if not specified
            if not webhook_name:
                webhook_name = name.replace(" ", "-").lower()

            # Create trigger configuration based on provider
            if provider == "datadog":
                return self._create_datadog_trigger(
                    trigger_id, name, workflow_file, webhook_name,
                    custom_headers, payload, encode_as, runner,
                    dd_api_key, dd_app_key, dd_site
                )
            elif provider == "github":
                return self._create_github_trigger(
                    trigger_id, name, workflow_file, repository,
                    events or ["push"], secret, runner, github_token
                )
            else:
                raise ValidationError(f"Unsupported provider: {provider}")

        except ValidationError:
            raise
        except Exception as e:
            error = TriggerError(f"Failed to create trigger: {str(e)}")
            capture_exception(error)
            raise error

    def list(
        self,
        provider: Optional[str] = None,
        kubiya_only: bool = False,
        repository: Optional[str] = None,
        dd_api_key: Optional[str] = None,
        dd_app_key: Optional[str] = None,
        dd_site: Optional[str] = None,
        github_token: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List all workflow triggers

        Args:
            provider: Filter by provider (datadog, github)
            kubiya_only: Show only webhooks that point to Kubiya API
            repository: GitHub repository (required for GitHub provider)
            dd_api_key: Datadog API key
            dd_app_key: Datadog application key
            dd_site: Datadog site
            github_token: GitHub token

        Returns:
            List of trigger information
        """
        try:
            all_webhooks = []

            # List Datadog webhooks if requested or no provider filter
            if not provider or provider == "datadog":
                try:
                    datadog_provider = self._get_datadog_provider(dd_api_key, dd_app_key, dd_site)
                    webhooks = datadog_provider.list_webhooks()
                    all_webhooks.extend(webhooks)
                except Exception as e:
                    logger.warning(f"Failed to list Datadog webhooks: {e}")

            # List GitHub webhooks if requested or no provider filter
            if not provider or provider == "github":
                if repository:
                    try:
                        github_provider = self._get_github_provider(github_token)
                        webhooks = github_provider.list_webhooks(repository)
                        all_webhooks.extend(webhooks)
                    except Exception as e:
                        logger.warning(f"Failed to list GitHub webhooks: {e}")
                elif provider == "github":
                    raise ValidationError("Repository is required when filtering by GitHub provider")

            # Filter by Kubiya-only if requested
            if kubiya_only:
                all_webhooks = [w for w in all_webhooks if w.get("is_kubiya", False)]

            return all_webhooks

        except ValidationError:
            raise
        except Exception as e:
            error = TriggerError(f"Failed to list triggers: {str(e)}")
            capture_exception(error)
            raise error

    def delete(
        self,
        provider: str,
        webhook_id: str,
        repository: Optional[str] = None,
        force: bool = False,
        dd_api_key: Optional[str] = None,
        dd_app_key: Optional[str] = None,
        dd_site: Optional[str] = None,
        github_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Delete a workflow trigger

        Args:
            provider: Provider type (datadog, github)
            webhook_id: Webhook ID or name to delete
            repository: GitHub repository (required for GitHub)
            force: Skip confirmation prompt
            dd_api_key: Datadog API key
            dd_app_key: Datadog application key
            dd_site: Datadog site
            github_token: GitHub token

        Returns:
            Deletion result
        """
        try:
            provider = provider.lower()
            if provider not in ["datadog", "github"]:
                raise ValidationError(f"Unsupported provider: {provider}")

            if provider == "github" and not repository:
                raise ValidationError("Repository is required for GitHub provider")

            # Delete based on provider
            if provider == "datadog":
                datadog_provider = self._get_datadog_provider(dd_api_key, dd_app_key, dd_site)
                datadog_provider.delete_trigger(webhook_id)
            elif provider == "github":
                github_provider = self._get_github_provider(github_token)
                github_provider.delete_trigger(repository, webhook_id)

            return {
                "success": True,
                "message": f"Webhook {webhook_id} deleted successfully from {provider}",
                "provider": provider,
                "webhook_id": webhook_id
            }

        except ValidationError:
            raise
        except Exception as e:
            error = TriggerError(f"Failed to delete trigger: {str(e)}")
            capture_exception(error)
            raise error

    def _create_datadog_trigger(
        self,
        trigger_id: str,
        name: str,
        workflow_file: str,
        webhook_name: str,
        custom_headers: Optional[str],
        payload: Optional[str],
        encode_as: str,
        runner: Optional[str],
        dd_api_key: Optional[str],
        dd_app_key: Optional[str],
        dd_site: Optional[str]
    ) -> Dict[str, Any]:
        """Create a Datadog trigger"""
        try:
            datadog_provider = self._get_datadog_provider(dd_api_key, dd_app_key, dd_site)

            # Create trigger object
            trigger = {
                "id": trigger_id,
                "name": name,
                "provider": "datadog",
                "workflow_ref": workflow_file,
                "status": "active",
                "created_at": time.time(),
                "updated_at": time.time(),
                "created_by": "api-user",
                "config": {
                    "webhook_name": webhook_name,
                    "custom_headers": custom_headers or "",
                    "payload": payload or "",
                    "encode_as": encode_as,
                    "environment": {"KUBIYA_RUNNER": runner} if runner else {}
                }
            }

            # Validate and create trigger
            datadog_provider.validate_config(trigger["config"])
            datadog_provider.create_trigger(trigger)

            return {
                "success": True,
                "trigger_id": trigger_id,
                "name": name,
                "provider": "datadog",
                "workflow": workflow_file,
                "webhook_name": webhook_name,
                "runner": runner,
                "webhook_url": f"https://api.kubiya.ai/api/v1/workflow?runner={runner or 'default'}&operation=execute_workflow"
            }

        except Exception as e:
            raise TriggerError(f"Failed to create Datadog trigger: {str(e)}")

    def _create_github_trigger(
        self,
        trigger_id: str,
        name: str,
        workflow_file: str,
        repository: str,
        events: List[str],
        secret: Optional[str],
        runner: Optional[str],
        github_token: Optional[str]
    ) -> Dict[str, Any]:
        """Create a GitHub trigger"""
        try:
            github_provider = self._get_github_provider(github_token)

            # Create trigger object
            trigger = {
                "id": trigger_id,
                "name": name,
                "provider": "github",
                "workflow_ref": workflow_file,
                "status": "active",
                "created_at": time.time(),
                "updated_at": time.time(),
                "created_by": "api-user",
                "config": {
                    "repository": repository,
                    "events": events,
                    "secret": secret or ""
                }
            }

            # Validate and create trigger
            github_provider.validate_config(trigger["config"])
            github_provider.create_trigger(trigger)

            return {
                "success": True,
                "trigger_id": trigger_id,
                "name": name,
                "provider": "github",
                "workflow": workflow_file,
                "repository": repository,
                "events": events,
                "runner": runner,
                "webhook_url": f"https://api.kubiya.ai/api/v1/workflow?runner={runner or 'default'}&operation=execute_workflow"
            }

        except Exception as e:
            raise TriggerError(f"Failed to create GitHub trigger: {str(e)}")

    def _get_datadog_provider(
        self,
        dd_api_key: Optional[str],
        dd_app_key: Optional[str],
        dd_site: Optional[str]
    ):
        """Get or create Datadog provider instance"""
        try:
            from kubiya_workflow_sdk.kubiya_services.services.trigger_providers import DatadogProvider
            return DatadogProvider(
                api_key=dd_api_key or os.getenv("DD_API_KEY"),
                app_key=dd_app_key or os.getenv("DD_APPLICATION_KEY"),
                site=dd_site or os.getenv("DD_SITE")
            )
        except ImportError:
            raise TriggerError("Datadog provider not available")

    def _get_github_provider(self, github_token: Optional[str]):
        """Get or create GitHub provider instance"""
        try:
            from kubiya_workflow_sdk.kubiya_services.services.trigger_providers import GitHubProvider
            return GitHubProvider(
                token=github_token or os.getenv("GITHUB_TOKEN")
            )
        except ImportError:
            raise TriggerError("GitHub provider not available")