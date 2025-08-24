"""
Secret service for managing secrets
"""
import json
import logging
import os
from typing import Optional, Dict, Any, List, Union

from kubiya_workflow_sdk.kubiya_services.constants import Endpoints
from kubiya_workflow_sdk.kubiya_services.exceptions import SecretError, SecretValidationError
from kubiya_workflow_sdk.kubiya_services.services.base import BaseService

logger = logging.getLogger(__name__)


class SecretService(BaseService):
    """Service for managing secrets"""

    def list(self) -> Union[List[Dict[str, Any]], str]:
        """
        List all secrets

        Returns:
            List of secrets or formatted string
        """
        endpoint = Endpoints.SECRETS_LIST
        try:
            return self._get(endpoint=endpoint).json()
        except Exception as e:
            raise SecretError("Failed to list secrets") from e

    def get(
        self,
        name: str
    ) -> Union[Dict[str, Any], str]:
        """
        Get secret details

        Args:
            name: Secret name

        Returns:
            Secret details dictionary or formatted string
        """

        endpoint = self._format_endpoint(Endpoints.SECRETS_GET, secret_name=name)
        try:
            return self._get(endpoint=endpoint).json()
        except Exception as e:
            raise SecretError(f"Failed to retrieve secret '{name}'") from e

    def value(
        self,
        name: str
    ) -> Union[str, Dict[str, str]]:
        """
        Get secret value

        Args:
            name: Secret name

        Returns:
            Secret value as string or dictionary with value key
        """
        if not name:
            raise SecretValidationError("Secret name is required")

        endpoint = self._format_endpoint(Endpoints.SECRETS_GET_VALUE, secret_name=name)

        try:
            return self._get(endpoint=endpoint).json()
        except Exception as e:
            raise SecretError(f"Failed to retrieve value for secret '{name}'") from e


    def create(
        self,
        name: str,
        value: Optional[str] = None,
        description: Optional[str] = None,
        from_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create new secret

        Args:
            name: Secret name
            value: Secret value
            description: Secret description
            from_file: Read value from file

        Returns:
            Creation response
        """

        if from_file and value:
            raise SecretValidationError("Cannot use both value and from_file")

        if from_file:
            if not os.path.exists(from_file):
                raise SecretError(f"File not found: {from_file}")
            with open(from_file, 'r') as f:
                value = f.read()

        if not value:
            raise SecretValidationError("Secret value must be provided via value or from_file")

        # Prepare request body
        request_body = {
            "name": name,
            "value": value
        }

        if description:
            request_body["description"] = description

        endpoint = Endpoints.SECRETS_CREATE
        resp = self._post(endpoint=endpoint, data=request_body, stream=False)

        if resp.status_code == 200:
            return {"message": f"Secret created successfully"}
        return resp.json()

    def update(
        self,
        name: str,
        value: Optional[str] = None,
        description: Optional[str] = None,
        from_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update secret value

        Args:
            name: Secret name
            value: New secret value
            description: New description
            from_file: Read new value from file

        Returns:
            Update response
        """

        if from_file and value:
            raise SecretValidationError("Cannot use both value and from_file")

        if from_file:
            if not os.path.exists(from_file):
                raise SecretError(f"File not found: {from_file}")
            with open(from_file, 'r') as f:
                value = f.read()

        if not value:
            raise SecretValidationError("Secret value must be provided via value or from_file")

        # Prepare request body
        request_body = {
            "value": value
        }

        if description:
            request_body["description"] = description

        endpoint = self._format_endpoint(Endpoints.SECRETS_UPDATE, secret_name=name)
        try:
            return self._put(endpoint=endpoint, data=request_body).json()
        except Exception as e:
            raise SecretError(f"Failed to update secret '{name}'") from e

    def delete(
        self,
        name: str,
    ) -> Dict[str, Any]:
        """
        Delete a secret

        Args:
            name: Secret name

        Returns:
            Deletion response
        """

        endpoint = self._format_endpoint(Endpoints.SECRETS_DELETE, secret_name=name)
        try:
            return self._delete(endpoint=endpoint).json()
        except Exception as e:
            raise SecretError(f"Failed to delete secret '{name}'") from e
