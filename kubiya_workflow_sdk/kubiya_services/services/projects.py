"""
Project service for managing projects
"""
import json
import logging
import os
from typing import Optional, Dict, Any, List, Union, Tuple

from kubiya_workflow_sdk.kubiya_services.constants import Endpoints
from kubiya_workflow_sdk.kubiya_services.exceptions import ProjectValidationError
from kubiya_workflow_sdk.kubiya_services.services.base import BaseService

logger = logging.getLogger(__name__)


class ProjectService(BaseService):
    """Service for managing projects"""

    def list(self) -> Dict[str, Any]:
        """
        List all projects

        Returns:
            List of projects or formatted string
        """
        endpoint = Endpoints.PROJECT_LIST
        response = self._get(endpoint=endpoint).json()

        return response

    def template_info(self, template_id: str) -> Union[Dict[str, Any], str]:
        """
        Get detailed information about a project template

        Args:
            template_id: Template ID or UUID

        Returns:
            Template details or formatted string
        """
        endpoint = self._format_endpoint(Endpoints.PROJECT_TEMPLATE_GET, template_id=template_id)
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

    def __create_project(
        self,
        template_id: str,
        name: str,
        description: str,
        variables: Optional[Dict[str, str]] = None
    ) -> Union[Dict[str, Any], str]:
        """
        Create a new project

        Args:
            template_id: Template ID to use for the project
            name: Project name
            description: Project description
            variables: Variable values as key-value pairs

        Returns:
            Created project details
        """
        # Initialize variables dict
        all_variables = variables or {}

        # Validate variables against template if template_id is provided
        if template_id:
            missing_vars, extra_vars, type_errors = self._validate_variables_against_template(template_id,
                                                                                              all_variables)

            # Error if any required variables are missing
            if missing_vars:
                raise ProjectValidationError(f"missing required variables: {', '.join(missing_vars)}")

            # Error if any type validation errors
            if type_errors:
                raise ProjectValidationError(f"variable type validation errors: {', '.join(type_errors)}")

            # Log extra variables as warning
            if extra_vars:
                logger.warning(
                    f"Warning: The following variables are not defined in the template: {', '.join(extra_vars)}")

        validated_vars = []
        for var_name, var_value in all_variables.items():
            validated_vars.append({
                "name": var_name,
                "value": var_value,
                "type": "string"  # Default type
            })

        request_body = {
            "template_id": template_id,
            "name": name,
            "description": description,
            "variables": validated_vars
        }

        endpoint = Endpoints.PROJECT_CREATE
        response = self._post(endpoint=endpoint, data=request_body)

        return response

    def create(
        self,
        name: str,
        template_id: Optional[str] = None,
        description: Optional[str] = None,
        variables: Optional[Dict[str, str]] = None,
        sensitive_variables: Optional[Dict[str, str]] = None,
        variables_file: Optional[str] = None,
        skip_var_validation: bool = False
    ) -> Union[Dict[str, Any], str]:
        """
        Create a new project

        Args:
            name: Project name (required)
            template_id: Template ID to use for the project
            description: Project description
            variables: Variable values in key=value format
            sensitive_variables: Sensitive variable values in key=value format
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
            if not os.path.exists(variables_file):
                raise ProjectValidationError(f"Variables file not found: {variables_file}")

            try:
                with open(variables_file, 'r') as f:
                    file_vars = json.load(f)
                    if not isinstance(file_vars, dict):
                        raise ProjectValidationError("Variables file must contain a JSON object")
                    # Convert all values to strings
                    for k, v in file_vars.items():
                        all_variables[k] = str(v)
            except json.JSONDecodeError as e:
                raise ProjectValidationError(f"Failed to parse variables file: {e}")
            except Exception as e:
                raise ProjectValidationError(f"Failed to read variables file: {e}")

        # Show project setup information
        setup_msg = f"\n🛠️  Setting up your project"
        if template_id:
            setup_msg += f" using template {template_id}"
        setup_msg += "..."
        logger.info(setup_msg)

        # Template validation variables
        template = None
        missing_required = []
        extra_vars = []
        type_errors = []
        missing_secrets = []

        # If using a template and not skipping validation, validate variables
        if template_id and not skip_var_validation:
            try:
                # Fetch the template to validate variables
                template = self.__get_template(template_id)

                # Check for required secrets (environment variables)
                for secret in template.get('secrets', []):
                    env_var = secret.get('to_env') or secret.get('toEnv') or secret.get('name')
                    if env_var and not os.environ.get(env_var):
                        missing_secrets.append(env_var)

                # Validate variables against template
                missing_required, extra_vars, type_errors = self._validate_variables_against_template(
                    template_id, all_variables
                )

            except Exception as e:
                raise ProjectValidationError(f"Failed to fetch template {template_id}: {e}")

        # Display validation results if using a template
        if template_id and not skip_var_validation:
            has_errors = missing_required or missing_secrets or type_errors
            has_warnings = extra_vars

            if has_errors or has_warnings:
                logger.info("")  # Empty line

            # Show missing required variables
            if missing_required:
                logger.error("❌ Missing required variables:")
                for var in missing_required:
                    logger.error(f"   - {var}")
                logger.info("")

            # Show missing secrets
            if missing_secrets:
                logger.error("❌ Missing required environment variables for secrets:")
                for secret in missing_secrets:
                    logger.error(f"   - {secret}")
                logger.info("")

            # Show extra variables as warning
            if extra_vars:
                logger.warning("⚠️  Variables not defined in template (will be passed through):")
                for var in extra_vars:
                    logger.warning(f"   - {var}")
                logger.info("")

            # Show type validation errors
            if type_errors:
                logger.error("❌ Variable type validation errors:")
                for error in type_errors:
                    logger.error(f"   - {error}")
                logger.info("")

            # If missing required variables or secrets, show template help and exit
            if missing_required or missing_secrets:
                if template and template.get('variables'):
                    logger.info("ℹ️  Required variables for this template:")
                    logger.info("NAME\tTYPE\tDESCRIPTION")

                    for var in template['variables']:
                        if var.get('required') and var.get('default') is None:
                            desc = var.get('description', 'No description')
                            logger.info(f"{var['name']}\t{var.get('type', 'string')}\t{desc}")

                    # Show resource variables
                    for resource in template.get('resources', []):
                        for var in resource.get('variables', []):
                            desc = var.get('description', 'No description')
                            logger.info(f"{var['name']}\t{var.get('type', 'string')}\t{desc}")

                    logger.info("")

                if template and template.get('secrets'):
                    logger.info("ℹ️  Required environment variables for secrets:")
                    for secret in template['secrets']:
                        env_var = secret.get('to_env') or secret.get('toEnv') or secret.get('name')
                        desc = secret.get('description', 'No description')
                        logger.info(f"   {env_var}: {desc}")

                    logger.info("")
                    logger.info("# Example export commands:")
                    for secret in template['secrets']:
                        env_var = secret.get('to_env') or secret.get('toEnv') or secret.get('name')
                        logger.info(f"export {env_var}=\"your-secret-value\"")
                    logger.info("")

                logger.info("To see all template details:")
                logger.info(f"   kubiya project template-info {template_id}")
                logger.info("")

                raise ProjectValidationError(
                    f"Missing required variables or environment variables for template {template_id}")

            # If there are type errors, exit
            if type_errors:
                raise ProjectValidationError("Variable type validation failed")

        # Create the project using the base create method
        try:
            result = self.__create_project(
                template_id=template_id or "",
                name=name,
                description=description or "",
                variables=all_variables
            )
        except Exception as e:
            raise ProjectValidationError(f"Failed to create project: {e}")

        return result

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
        project_id: str
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
        project_id: str
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
        repository: Optional[str] = None
    ) -> Dict[str, Any]:
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
        template_id: str
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
        auto_approve: bool = False
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
        plan_id: str
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

    def __validate_variable_type(
        self,
        value: str,
        expected_type: str
    ) -> Tuple[bool, str]:
        """
        Validate variable type.

        Args:
            value: Variable value as string
            expected_type: Expected type

        Returns:
            Tuple of (is_valid, error_message)
        """
        if expected_type in ["string", ""]:
            return True, ""

        elif expected_type in ["number", "int", "integer"]:
            try:
                int(value)
                return True, ""
            except ValueError:
                return False, f"expected {expected_type} but got '{value}'"

        elif expected_type == "float":
            try:
                float(value)
                return True, ""
            except ValueError:
                return False, f"expected float but got '{value}'"

        elif expected_type in ["bool", "boolean"]:
            lower_value = value.lower()
            if lower_value in ["true", "false"]:
                return True, ""
            return False, f"expected boolean but got '{value}'"

        elif expected_type in ["list", "array"]:
            # Check if it starts with [ and ends with ]
            if value.startswith("[") and value.endswith("]"):
                try:
                    json.loads(value)
                    return True, ""
                except json.JSONDecodeError:
                    return False, f"value '{value}' is not a valid array"
            # Otherwise try to parse as comma-separated values
            return True, ""  # Accept comma-separated values as valid arrays

        elif expected_type in ["map", "object"]:
            # Check if it starts with { and ends with }
            if value.startswith("{") and value.endswith("}"):
                try:
                    result = json.loads(value)
                    if not isinstance(result, dict):
                        return False, f"value '{value}' is not a valid object"
                    return True, ""
                except json.JSONDecodeError:
                    return False, f"value '{value}' is not a valid object"
            # Otherwise try to parse as key=value pairs
            try:
                items = value.split(",")
                for item in items:
                    parts = item.strip().split("=", 1)
                    if len(parts) != 2:
                        return False, f"value '{item}' is not a valid key=value pair"
                return True, ""
            except Exception:
                return False, f"value '{value}' is not a valid object"

        else:
            # For unknown types, just pass the string value
            return True, ""


    def _validate_variables_against_template(
        self,
        template_id: str,
        variables: Dict[str, str]
    ) -> Tuple[List[str], List[str], List[str]]:
        """
        Validate variables against a template

        Args:
            template_id: Template ID
            variables: Variables to validate

        Returns:
            Tuple of (missing_required, extra_vars, type_errors)
        """
        # Get the template
        template = self.__get_template(template_id)

        # Collect all variables from template and resources
        all_variables = {}
        required_vars = {}

        # Add template variables
        for var in template.get('variables', []):
            all_variables[var['name']] = var
            if var.get('required') and var.get('default') is None:
                required_vars[var['name']] = True

        # Add resource variables
        for resource in template.get('resources', []):
            for var in resource.get('variables', []):
                all_variables[var['name']] = {
                    'name': var['name'],
                    'type': var.get('type', 'string'),
                    'default': var.get('default'),
                    'description': var.get('description'),
                    'required': True  # Consider resource variables required
                }
                required_vars[var['name']] = True

        # Find missing required variables
        missing_required = []
        for name in required_vars:
            if name not in variables:
                missing_required.append(name)

        # Find variables not in template
        extra_vars = []
        for name in variables:
            if name not in all_variables:
                extra_vars.append(name)

        # Validate types of provided variables
        type_errors = []
        for name, value in variables.items():
            if name in all_variables:
                template_var = all_variables[name]
                expected_type = template_var.get('type', 'string')
                is_valid, error_msg = self.__validate_variable_type(value, expected_type)
                if not is_valid:
                    type_errors.append(f"{name}: {error_msg}")

        return missing_required, extra_vars, type_errors