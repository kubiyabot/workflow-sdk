"""
User service for managing users and groups
"""
import logging
from typing import Optional, Dict, Any, List, Union

from kubiya_workflow_sdk import capture_exception
from kubiya_workflow_sdk.kubiya_services.services.base import BaseService
from kubiya_workflow_sdk.kubiya_services.constants import Endpoints
from kubiya_workflow_sdk.kubiya_services.exceptions import UserError, GroupError

logger = logging.getLogger(__name__)


class UserService(BaseService):
    """Service for managing users and groups"""

    def list_users(
        self,
        limit: Optional[int] = 100,
        page: int = 1
    ) -> Union[List[Dict[str, Any]], str]:
        """
        List all users in the organization

        Args:
            limit: Number of users to return (default: 100)
            page: Page number for pagination (default: 1)

        Returns:
            List of users or formatted text output
        """
        try:
            # The users endpoint uses v2 API
            endpoint = self._format_endpoint(Endpoints.USER_LIST)

            # Add pagination parameters
            separator = '&' if '?' in endpoint else '?'
            endpoint = f"{endpoint}{separator}limit={limit}&page={page}"

            response = self._get(endpoint=endpoint).json()

            # Handle v2 API response format with items
            if isinstance(response, dict) and "items" in response:
                users = response["items"]
            elif isinstance(response, list):
                users = response
            else:
                users = []

            return users

        except Exception as e:
            error = UserError(f"Failed to list users: {str(e)}")
            capture_exception(error)
            raise error

    def list_groups(self) -> Union[List[Dict[str, Any]], str]:
        """
        List all groups in the organization

        Returns:
            List of groups or formatted text output
        """
        try:
            endpoint = self._format_endpoint(Endpoints.GROUP_LIST)
            response = self._get(endpoint=endpoint).json()

            # Handle response format
            if isinstance(response, list):
                groups = response
            elif isinstance(response, dict) and "groups" in response:
                groups = response["groups"]
            else:
                groups = []

            return groups

        except Exception as e:
            error = GroupError(f"Failed to list groups: {str(e)}")
            capture_exception(error)
            raise error
