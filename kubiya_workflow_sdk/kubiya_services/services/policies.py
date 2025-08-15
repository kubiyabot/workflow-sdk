"""
Policy service for managing OPA policies
"""
import json
import logging
from typing import Optional, Dict, Any, List, Union

from kubiya_workflow_sdk.kubiya_services.constants import Endpoints
from kubiya_workflow_sdk.kubiya_services.exceptions import PolicyValidationError, PolicyError
from kubiya_workflow_sdk.kubiya_services.services.base import BaseService

logger = logging.getLogger(__name__)


class PolicyService(BaseService):
    """Service for managing OPA policies"""

    def list(self) -> Union[List[Dict[str, Any]], str]:
        """
        List all OPA policies

        Returns:
            List of policies or JSON string
        """
        endpoint = Endpoints.POLICY_LIST

        return self._get(endpoint=endpoint).json()

    def get(
        self,
        policy_name: str
    ) -> Union[Dict[str, Any], str]:
        """
        Get policy details

        Args:
            policy_name: Name of the policy to retrieve

        Returns:
            Policy details or JSON string
        """

        endpoint = self._format_endpoint(Endpoints.POLICY_GET, policy_name=policy_name)

        return self._get(endpoint=endpoint).json()

    def create(
        self,
        name: str,
        policy: Optional[str] = None,
        file: Optional[str] = None,
        env: Optional[List[str]] = None,
        validate: bool = True
    ) -> Dict[str, Any]:
        """
        Create a new OPA policy

        Args:
            name: Policy name
            policy: Policy content directly
            file: Policy file path (alternative to policy parameter)
            env: Target environments (list of environment names)
            validate: Validate policy before creating (default: True)

        Returns:
            Created policy details
        """
        # Get policy content
        policy_content = self._get_policy_content(policy=policy, file=file)

        # Prepare request body
        request_body = {
            "name": name,
            "env": env if env else [],
            "policy": policy_content
        }

        # Validate policy if requested
        if validate:
            validation_result = self.validate(
                name=name,
                policy=policy_content,
                env=env
            )

            if not validation_result.get("valid", False):
                errors = validation_result.get("errors", ["Unknown validation error"])
                raise PolicyValidationError(f"Policy validation failed: {', '.join(errors)}")

        endpoint = Endpoints.POLICY_CREATE

        return self._post(endpoint=endpoint, data=request_body).json()

    def update(
        self,
        policy_name: str,
        policy: Optional[str] = None,
        file: Optional[str] = None,
        env: Optional[List[str]] = None,
        validate: bool = True
    ) -> Dict[str, Any]:
        """
        Update an existing OPA policy

        Args:
            policy_name: Name of the policy to update
            policy: Policy content directly
            file: Policy file path (alternative to policy parameter)
            env: Target environments (list of environment names)
            validate: Validate policy before updating (default: True)

        Returns:
            Updated policy details
        """
        # Get existing policy first
        existing_policy = self.get(policy_name)

        # Update fields if provided
        if env is not None:
            existing_policy["env"] = env

        if policy or file:
            policy_content = self._get_policy_content(policy=policy, file=file)
            existing_policy["policy"] = policy_content

        # Validate policy if requested
        if validate:
            validation_result = self.validate(
                name=existing_policy["name"],
                policy=existing_policy["policy"],
                env=existing_policy.get("env", [])
            )

            if not validation_result.get("valid", False):
                errors = validation_result.get("errors", ["Unknown validation error"])
                raise PolicyValidationError(f"Policy validation failed: {', '.join(errors)}")

        endpoint = self._format_endpoint(Endpoints.POLICY_UPDATE, policy_name=policy_name)

        return self._put(endpoint=endpoint, data=existing_policy).json()

    def delete(
        self,
        policy_name: str,
        confirm: bool = False
    ) -> Dict[str, Any]:
        """
        Delete an OPA policy

        Args:
            policy_name: Name of the policy to delete
            confirm: Confirm deletion (default: False)

        Returns:
            Deletion status
        """
        if not confirm:
            raise PolicyError(f"Deletion not confirmed for policy '{policy_name}'. Set confirm=True to proceed.")

        endpoint = self._format_endpoint(Endpoints.POLICY_DELETE, policy_name=policy_name)

        return self._delete(endpoint=endpoint).json()

    def validate(
        self,
        name: str,
        policy: Optional[str] = None,
        file: Optional[str] = None,
        env: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Validate an OPA policy

        Args:
            name: Policy name
            policy: Policy content directly
            file: Policy file path (alternative to policy parameter)
            env: Target environments (list of environment names)

        Returns:
            Validation result with 'valid' boolean and 'errors' list
        """
        # Get policy content
        policy_content = self._get_policy_content(policy=policy, file=file)

        # Prepare request body
        request_body = {
            "name": name,
            "env": env if env else [],
            "policy": policy_content
        }

        endpoint = Endpoints.POLICY_VALIDATE

        return self._post(endpoint=endpoint, data=request_body).json()

    def evaluate(
        self,
        policy: Optional[str] = None,
        policy_file: Optional[str] = None,
        input: Optional[Union[Dict[str, Any], str]] = None,
        input_file: Optional[str] = None,
        data: Optional[Union[Dict[str, Any], str]] = None,
        data_file: Optional[str] = None,
        query: str = "data"
    ) -> Dict[str, Any]:
        """
        Evaluate a policy with input data

        Args:
            policy: Policy content directly
            policy_file: Policy file path (alternative to policy parameter)
            input: Input JSON (dict or JSON string)
            input_file: Input JSON file path
            data: Data JSON (dict or JSON string)
            data_file: Data JSON file path
            query: Query string (default: 'data')

        Returns:
            Evaluation result with 'result' field and optional 'error' field
        """
        # Get policy content
        policy_content = self._get_policy_content(policy=policy, file=policy_file)

        # Parse input
        input_data = self._parse_json_input(
            json_data=input,
            json_file=input_file,
            default={}
        )

        # Parse data
        data_content = self._parse_json_input(
            json_data=data,
            json_file=data_file,
            default={}
        )

        # Prepare request body
        request_body = {
            "input": input_data,
            "policy": policy_content,
            "data": data_content,
            "query": query
        }

        endpoint = Endpoints.POLICY_EVALUATE

        return self._post(endpoint=endpoint, data=request_body).json()

    def test(
        self,
        tool_name: Optional[str] = None,
        workflow_file: Optional[str] = None,
        args: Optional[Union[Dict[str, Any], str]] = None,
        args_file: Optional[str] = None,
        params: Optional[Union[Dict[str, Any], str]] = None,
        params_file: Optional[str] = None,
        runner: str = "default"
    ) -> Dict[str, Any]:
        """
        Test tool or workflow execution permission

        Args:
            tool_name: Tool name (for tool testing)
            workflow_file: Workflow definition file (for workflow testing)
            args: Tool arguments (dict or JSON string)
            args_file: Tool arguments JSON file
            params: Workflow parameters (dict or JSON string)
            params_file: Workflow parameters JSON file
            runner: Runner name (default: 'default')

        Returns:
            Test result with 'allowed' boolean and optional 'message' or 'issues'
        """
        if tool_name:
            # Test tool permission
            return self._test_tool_permission(
                tool_name=tool_name,
                args=args,
                args_file=args_file,
                runner=runner
            )
        elif workflow_file:
            # Test workflow permission
            return self._test_workflow_permission(
                workflow_file=workflow_file,
                params=params,
                params_file=params_file,
                runner=runner
            )
        else:
            raise PolicyError("Either 'tool_name' or 'workflow_file' must be provided")

    # Private helper methods

    def _get_policy_content(
        self,
        policy: Optional[str] = None,
        file: Optional[str] = None
    ) -> str:
        """
        Get policy content from either direct string or file

        Args:
            policy: Policy content directly
            file: Policy file path

        Returns:
            Policy content string
        """
        if policy:
            return policy
        elif file:
            try:
                with open(file, 'r') as f:
                    return f.read()
            except IOError as e:
                raise PolicyError(f"Failed to read policy file: {e}")
        else:
            raise PolicyError("Either 'policy' or 'file' must be provided")

    def _parse_json_input(
        self,
        json_data: Optional[Union[Dict[str, Any], str]] = None,
        json_file: Optional[str] = None,
        default: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Parse JSON input from various sources

        Args:
            json_data: JSON data (dict or JSON string)
            json_file: JSON file path
            default: Default value if nothing provided

        Returns:
            Parsed JSON as dictionary
        """
        if json_data:
            if isinstance(json_data, dict):
                return json_data
            elif isinstance(json_data, str):
                try:
                    return json.loads(json_data)
                except json.JSONDecodeError as e:
                    raise PolicyError(f"Failed to parse JSON: {e}")
        elif json_file:
            try:
                with open(json_file, 'r') as f:
                    return json.load(f)
            except (IOError, json.JSONDecodeError) as e:
                raise PolicyError(f"Failed to read JSON file: {e}")

        return default if default is not None else {}

    def _test_tool_permission(
        self,
        tool_name: str,
        args: Optional[Union[Dict[str, Any], str]] = None,
        args_file: Optional[str] = None,
        runner: str = "default"
    ) -> Dict[str, Any]:
        """
        Test tool execution permission

        Args:
            tool_name: Tool name
            args: Tool arguments (dict or JSON string)
            args_file: Tool arguments JSON file
            runner: Runner name

        Returns:
            Test result with 'allowed' boolean and optional 'message'
        """
        # Parse arguments
        tool_args = self._parse_json_input(
            json_data=args,
            json_file=args_file,
            default={}
        )

        # Prepare input for policy evaluation
        input_data = {
            "action": "tool_execution",
            "tool_name": tool_name,
            "args": tool_args,
            "runner": runner,
            "user": {}  # User context would be added by the client
        }

        # Evaluate using standard tool permission query
        evaluation_result = self.evaluate(
            policy="",  # Server will use the configured policy
            input=input_data,
            query="data.tools.allow"
        )

        # Process result
        if evaluation_result.get("error"):
            return {
                "allowed": False,
                "message": evaluation_result["error"]
            }

        result = evaluation_result.get("result", False)

        # Handle boolean result
        if isinstance(result, bool):
            return {
                "allowed": result,
                "message": "Permission granted" if result else "Permission denied"
            }

        # Handle complex result
        if isinstance(result, dict):
            allowed = result.get("allow", False)
            message = result.get("message", "")
            return {
                "allowed": allowed,
                "message": message
            }

        return {
            "allowed": False,
            "message": "Policy evaluation result format not recognized"
        }

    def _test_workflow_permission(
        self,
        workflow_file: str,
        params: Optional[Union[Dict[str, Any], str]] = None,
        params_file: Optional[str] = None,
        runner: str = "default"
    ) -> Dict[str, Any]:
        """
        Test workflow execution permission

        Args:
            workflow_file: Workflow definition file
            params: Workflow parameters (dict or JSON string)
            params_file: Workflow parameters JSON file
            runner: Runner name

        Returns:
            Test result with 'allowed' boolean and 'issues' list
        """
        # Read workflow definition
        try:
            with open(workflow_file, 'r') as f:
                workflow_content = f.read()
                workflow_def = json.loads(workflow_content)
        except (IOError, json.JSONDecodeError) as e:
            raise PolicyError(f"Failed to read workflow file: {e}")

        # Parse parameters
        workflow_params = self._parse_json_input(
            json_data=params,
            json_file=params_file,
            default={}
        )

        issues = []

        # Validate each step in the workflow
        steps = workflow_def.get("steps", [])
        for i, step in enumerate(steps):
            step_name = step.get("name", f"step_{i + 1}")

            # Check if step has tool execution
            executor = step.get("executor", {})
            if executor.get("type") == "tool":
                config = executor.get("config", {})
                tool_def = config.get("tool_def", {})
                tool_name = tool_def.get("name")

                if not tool_name:
                    issues.append(f"Step '{step_name}': Tool name missing")
                    continue

                # Extract tool args
                tool_args = config.get("args", {})

                # Test tool permission
                tool_test_result = self._test_tool_permission(
                    tool_name=tool_name,
                    args=tool_args,
                    runner=runner
                )

                if not tool_test_result.get("allowed", False):
                    error_msg = f"Step '{step_name}': No permission to execute tool '{tool_name}'"
                    if tool_test_result.get("message"):
                        error_msg += f" - {tool_test_result['message']}"
                    issues.append(error_msg)

        # Overall workflow validation
        input_data = {
            "action": "workflow_execution",
            "workflow_def": workflow_def,
            "params": workflow_params,
            "runner": runner,
            "user": {}  # User context would be added by the client
        }

        # Evaluate using standard workflow permission query
        evaluation_result = self.evaluate(
            policy="",  # Server will use the configured policy
            input=input_data,
            query="data.workflows.allow"
        )

        # Process result
        if evaluation_result.get("error"):
            issues.append(f"Workflow policy error: {evaluation_result['error']}")
            return {
                "allowed": False,
                "issues": issues
            }

        result = evaluation_result.get("result", True)

        # Handle boolean result
        if isinstance(result, bool):
            if not result:
                issues.append("Workflow execution denied by policy")
            return {
                "allowed": result and len(issues) == 0,
                "issues": issues
            }

        # Handle complex result
        if isinstance(result, dict):
            allowed = result.get("allow", True)
            if not allowed and result.get("message"):
                issues.append(result["message"])

            return {
                "allowed": allowed and len(issues) == 0,
                "issues": issues
            }

        # Default to allow if policy format not recognized but check for step issues
        return {
            "allowed": len(issues) == 0,
            "issues": issues
        }
