"""
Integration service for managing integrations
"""
import logging
from typing import Optional, Dict, Any

from kubiya_workflow_sdk.kubiya_services.constants import Endpoints
from kubiya_workflow_sdk.kubiya_services.exceptions import IntegrationError, IntegrationNotFoundError
from kubiya_workflow_sdk.kubiya_services.services.base import BaseService

logger = logging.getLogger(__name__)


class IntegrationService(BaseService):
    """Service for managing integrations"""

    def activate(self, name: str) -> Dict[str, Any]:
        """
        Activate an integration

        Args:
            name: Name of the integration to activate

        Returns:
            Dictionary containing activation result and install URL

        Raises:
            IntegrationError: If integration type is not supported or activation fails
            IntegrationNotFoundError: If integration already exists
        """
        if name == "github_app":
            install_url = self._github_app()

            return {
                "success": True,
                "message": "GitHub App integration activated successfully!",
                "install_url": install_url,
                "instructions": "Please open this URL in your browser to complete the installation."
            }
        else:
            supported_integrations = ["github_app"]
            raise IntegrationError(
                f"integration type {name} is not supported only: {', '.join(supported_integrations)}"
            )

    def _github_app(self) -> str:
        """
        Handle GitHub App integration activation

        Returns:
            Installation URL for GitHub App

        Raises:
            IntegrationNotFoundError: If integration already exists
            IntegrationError: If failed to create GitHub app integration
        """
        name = "github_app"
        already_exist_error = "integration github app already exist"
        create_error = "failed to create github app integration"

        # Check if integration already exists
        item = self._get_integration(name)

        if item is not None and item.get("name") == name:
            raise IntegrationNotFoundError(already_exist_error)

        # Create GitHub integration and get install URL
        install_url = self._create_github_integration()

        if not install_url or len(install_url) <= 0:
            raise IntegrationError(create_error)

        return install_url

    def _get_integration(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get integration by name

        Args:
            name: Name of the integration

        Returns:
            Integration data or None if not found

        Raises:
            IntegrationError: If API request fails
        """
        try:
            endpoint = self._format_endpoint(Endpoints.INTEGRATION_GET, integration_name=name)
            return self._get(endpoint=endpoint).json()

        except Exception as e:
            # If we get a 404 or similar error, the integration doesn't exist
            logger.debug(f"Integration {name} not found: {e}")
            return None

    def _create_github_integration(self) -> str:
        """
        Create GitHub App integration and return install URL

        Returns:
            Installation URL for GitHub App

        Raises:
            IntegrationError: If API request fails or unexpected response
        """
        endpoint = self._format_endpoint(Endpoints.INTEGRATIONS_GITHUB, integration_name="github_app")

        try:
            return self._get(endpoint=endpoint).json()
        except Exception as e:
            raise IntegrationError(f"Failed to create install url. unexpected error: {str(e)}")
