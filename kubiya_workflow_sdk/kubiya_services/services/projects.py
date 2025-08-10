"""
Project service for managing projects
"""
import json
import logging
import os
import time
from typing import Optional, Dict, Any, List, Union

from kubiya_workflow_sdk.kubiya_services.constants import Endpoints
from kubiya_workflow_sdk.kubiya_services.services.base import BaseService

logger = logging.getLogger(__name__)


class ProjectService(BaseService):
    """Service for managing projects"""

    def list(self) -> Union[List[Dict[str, Any]], str]:
        """
        List all projects

        Returns:
            List of projects or formatted string
        """
        endpoint = Endpoints.PROJECT_LIST
        response = self._get(endpoint=endpoint).json()

        return response

    def __get(
        self,
        project_id: str,
    ) -> Union[Dict[str, Any], str]:
        """
        Get project details

        Args:
            project_id: Project UUID or ID

        Returns:
            Project details or formatted string
        """
        endpoint = self._format_endpoint(Endpoints.PROJECT_GET, project_id=project_id)
        response = self._get(endpoint=endpoint).json()

        return response

    def create(
        self,
        name: str,
        template_id: Optional[str] = None,
        description: Optional[str] = None,
        variables: Optional[Dict[str, str]] = None,
        sensitive_variables: Optional[Dict[str, str]] = None,
        variables_file: Optional[str] = None,
        skip_var_validation: bool = False,
    ) -> Union[Dict[str, Any], str]:
        """
        Create a new project

        Args:
            name: Project name
            template_id: Template ID to use for the project
            description: Project description
            variables: Variable values in key=value format
            sensitive_variables: Sensitive variable values
            variables_file: Path to a JSON file containing variables
            skip_var_validation: Skip validation of variables against template

        Returns:
            Created project details or formatted string
        """
        # Initialize variables dict
        all_variables = {}

        # Add provided variables
        if variables:
            all_variables.update(variables)

        # Add sensitive variables
        if sensitive_variables:
            all_variables.update(sensitive_variables)

        # Load variables from file if provided
        if variables_file:
            with open(variables_file, 'r') as f:
                file_vars = json.load(f)
                all_variables.update(file_vars)

        # Validate variables against template if not skipping
        if template_id and not skip_var_validation:
            # Get template details for validation
            template = self.__get_template(template_id)

            # Check for required variables
            required_vars = []
            for var in template.get('variables', []):
                if var.get('required') and var.get('default') is None:
                    required_vars.append(var['name'])

            # Check for required resource variables
            for resource in template.get('resources', []):
                for var in resource.get('variables', []):
                    if var.get('default') is None:
                        required_vars.append(var['name'])

            # Check for missing required variables
            missing_vars = [v for v in required_vars if v not in all_variables]
            if missing_vars:
                raise ValueError(f"Missing required variables: {', '.join(missing_vars)}")

            # Check for required secrets (environment variables)
            missing_secrets = []
            for secret in template.get('secrets', []):
                env_var = secret.get('toEnv', secret.get('name'))
                if env_var and not os.environ.get(env_var):
                    missing_secrets.append(env_var)

            if missing_secrets:
                raise ValueError(f"Missing required environment variables for secrets: {', '.join(missing_secrets)}")

        # Prepare request body
        request_body = {
            "name": name,
            "usecase_id": template_id,
            "description": description or "",
            "variables": all_variables
        }

        # Remove None values
        request_body = {k: v for k, v in request_body.items() if v is not None}

        endpoint = Endpoints.PROJECT_CREATE
        response = self._post(endpoint=endpoint, data=request_body).json()

        return response

    def update(
        self,
        project_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        variables: Optional[Dict[str, str]] = None,
    ) -> Union[Dict[str, Any], str]:
        """
        Update a project

        Args:
            project_id: Project UUID or ID
            name: New project name
            description: New project description
            variables: Variable values to update

        Returns:
            Updated project details or formatted string
        """
        # Get current project to preserve values not being updated
        current_project = self.__get(project_id)

        # Update fields if provided
        updated_name = name if name is not None else current_project.get('name')
        updated_description = description if description is not None else current_project.get('description')

        # Merge variables
        updated_variables = {}

        # Extract existing variables
        if current_project.get('variables'):
            for var_obj in current_project['variables']:
                if var_obj.get('name'):
                    updated_variables[var_obj['name']] = var_obj.get('value')

        # Add/update with new variables
        if variables:
            updated_variables.update(variables)

        # Prepare request body
        request_body = {
            "name": updated_name,
            "description": updated_description,
            "variables": updated_variables
        }

        endpoint = self._format_endpoint(Endpoints.PROJECT_UPDATE, project_id=project_id)
        response = self._put(endpoint=endpoint, data=request_body).json()

        return response

    def delete(
        self,
        project_id: str,
    ) -> Dict[str, Any]:
        """
        Delete a project

        Args:
            project_id: Project UUID or ID

        Returns:
            Deletion result
        """
        endpoint = self._format_endpoint(Endpoints.PROJECT_DELETE, project_id=project_id)
        response = self._delete(endpoint=endpoint).json()

        return response

    def describe(
        self,
        project_id: str,
    ) -> Union[Dict[str, Any], str]:
        """
        Get detailed project information

        Args:
            project_id: Project UUID or ID

        Returns:
            Detailed project information or formatted string
        """
        return self.__get(project_id)

    def templates(
        self,
        repository: Optional[str] = None,
    ) -> Union[List[Dict[str, Any]], str]:
        """
        List available project templates

        Args:
            repository: Repository URL to fetch templates from

        Returns:
            List of templates or formatted string
        """
        endpoint = Endpoints.PROJECT_TEMPLATES_LIST

        # Add repository parameter if provided
        if repository:
            endpoint += f"?repository={repository}"

        response = self._get(endpoint=endpoint).json()

        return response

    def __get_template(
        self,
        template_id: str,
    ) -> Union[Dict[str, Any], str]:
        """
        Get detailed template information

        Args:
            template_id: Template ID or UUID

        Returns:
            Template details or formatted string
        """
        endpoint = self._format_endpoint(Endpoints.PROJECT_TEMPLATE_GET, template_id=template_id)
        response = self._get(endpoint=endpoint).json()

        return response

    def plan(
        self,
        project_id: str,
        auto_approve: bool = False,
    ) -> Dict[str, Any]:
        """
        Create a plan for a project

        Args:
            project_id: Project UUID or ID
            auto_approve: Auto-approve the plan

        Returns:
            Plan details
        """
        request_body = {
            "project_id": project_id
        }

        endpoint = self._format_endpoint(Endpoints.PROJECT_PLAN_CREATE, project_id=project_id)
        response = self._post(endpoint=endpoint, data=request_body).json()

        # Auto-approve if requested and there are changes
        if auto_approve and response.get('changes'):
            plan_id = response.get('plan_id')
            if plan_id:
                execution = self.approve(plan_id)

                return execution

        return response

    def approve(
        self,
        plan_id: str,
    ) -> Dict[str, Any]:
        """
        Approve a project plan

        Args:
            plan_id: Plan ID

        Returns:
            Execution details
        """
        request_body = {
            "action": "approve"
        }

        endpoint = self._format_endpoint(Endpoints.PROJECT_PLAN_APPROVE, plan_id=plan_id)
        response = self._put(endpoint=endpoint, data=request_body)

        return response

    def __get_execution(
            self,
            execution_id: str
    ) -> Dict[str, Any]:
        """
        Get execution details

        Args:
            execution_id: Execution ID

        Returns:
            Execution details
        """
        endpoint = self._format_endpoint(Endpoints.PROJECT_EXECUTION_GET, execution_id=execution_id)
        response = self._get(endpoint=endpoint)

        return response

    def __get_execution_logs(
            self,
            execution_id: str
    ) -> List[str]:
        """
        Get execution logs

        Args:
            execution_id: Execution ID

        Returns:
            List of log lines
        """
        endpoint = self._format_endpoint(Endpoints.PROJECT_EXECUTION_LOGS, execution_id=execution_id)
        response = self._get(endpoint=endpoint)

        # Handle different response formats
        if isinstance(response, list):
            return response
        elif isinstance(response, dict):
            return response.get('logs', [])
        else:
            return [str(response)]

    def __follow_execution(
        self,
        execution_id: str,
        poll_interval: int = 1
    ) -> None:
        """
        Follow execution logs in real-time

        Args:
            execution_id: Execution ID
            poll_interval: Polling interval in seconds
        """
        last_log_count = 0

        while True:
            time.sleep(poll_interval)

            # Get execution status
            execution = self.__get_execution(execution_id)
            status = execution.get('status', '').lower()

            # Get logs
            logs = self.__get_execution_logs(execution_id)

            # Print new logs
            for i in range(last_log_count, len(logs)):
                logger.info(logs[i])
            last_log_count = len(logs)

            # Check if execution is complete
            if status in ['completed', 'failed']:
                if status == 'completed':
                    logger.info("✅ Execution completed")
                else:
                    logger.error("❌ Execution failed")
                break
