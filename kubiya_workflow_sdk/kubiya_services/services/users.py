"""
User service for managing users and groups
"""
import logging
from typing import Optional, Dict, Any, List, Union

from kubiya_workflow_sdk import capture_exception
from kubiya_workflow_sdk.kubiya_services.services.base import BaseService
from kubiya_workflow_sdk.kubiya_services.constants import Endpoints
from kubiya_workflow_sdk.kubiya_services.exceptions import UserError



logger = logging.getLogger(__name__)


class UserService(BaseService):
    """Service for managing users and groups"""

    def list_users(
            self,
            output_format: str = "json",
            limit: Optional[int] = 100,
            page: int = 1
    ) -> Union[List[Dict[str, Any]], str]:
        """
        List all users in the organization

        Args:
            output_format: Output format (json|text)
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

            if output_format == "json":
                return users
            elif output_format == "text":
                return self._format_users_table(users)
            else:
                return users

        except Exception as e:
            error = UserError(f"Failed to list users: {str(e)}")
            capture_exception(error)
            raise error

    def list_groups(
            self,
            output_format: str = "json"
    ) -> Union[List[Dict[str, Any]], str]:
        """
        List all groups in the organization

        Args:
            output_format: Output format (json|text)

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

            if output_format == "json":
                return groups
            elif output_format == "text":
                return self._format_groups_table(groups)
            else:
                return groups

        except Exception as e:
            error = UserError(f"Failed to list groups: {str(e)}")
            capture_exception(error)
            raise error


    def _format_users_table(self, users: List[Dict[str, Any]]) -> str:
        """
        Format users as a table string

        Args:
            users: List of user objects

        Returns:
            Formatted table string
        """
        if not users:
            return "No users found."

        # Sort users by email for consistent output
        sorted_users = sorted(users, key=lambda x: x.get("email", ""))

        # Build table
        lines = []
        lines.append("EMAIL\tNAME\tUUID\tSTATUS\tGROUPS")

        for user in sorted_users:
            email = user.get("email", "-")
            name = user.get("name", "-") or "-"
            uuid = user.get("uuid", "-")
            status = user.get("user_status", user.get("status", "-"))

            groups = user.get("groups", [])
            if isinstance(groups, list):
                if len(groups) == 0:
                    groups_str = "none"
                else:
                    groups_str = f"{len(groups)} groups"
            else:
                groups_str = "none"

            lines.append(f"{email}\t{name}\t{uuid}\t{status}\t{groups_str}")

        return "\n".join(lines)

    def _format_groups_table(self, groups: List[Dict[str, Any]]) -> str:
        """
        Format groups as a table string

        Args:
            groups: List of group objects

        Returns:
            Formatted table string
        """
        if not groups:
            return "No groups found."

        # Sort groups - system groups first, then by name
        def sort_key(group):
            system = group.get("system", False)
            name = group.get("name", "")
            return (not system, name)  # not system puts True (system) groups first

        sorted_groups = sorted(groups, key=sort_key)

        # Build table
        lines = []
        lines.append("NAME\tUUID\tDESCRIPTION\tTYPE")

        for group in sorted_groups:
            name = group.get("name", "-")
            uuid = group.get("uuid", "-")
            description = group.get("description", "-") or "-"

            system = group.get("system", False)
            group_type = "System" if system else "Custom"

            lines.append(f"{name}\t{uuid}\t{description}\t{group_type}")

        return "\n".join(lines)
