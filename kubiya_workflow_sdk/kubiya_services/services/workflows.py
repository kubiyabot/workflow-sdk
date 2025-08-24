"""
Workflow service for managing workflows
"""
import json
import logging
from typing import Optional, Dict, Any, Union, Generator
from kubiya_workflow_sdk.kubiya_services.services.base import BaseService
from kubiya_workflow_sdk.kubiya_services.constants import Endpoints
from kubiya_workflow_sdk.kubiya_services.exceptions import WorkflowExecutionError

from kubiya_workflow_sdk import capture_exception

logger = logging.getLogger(__name__)


class WorkflowService(BaseService):
    """Service for managing workflows"""

    def execute(
        self,
        workflow_definition: Union[Dict[str, Any], str],
        parameters: Optional[Dict[str, Any]] = None,
        stream: bool = True,
        runner: Optional[str] = None
    ) -> Union[Dict[str, Any], Generator[str, None, None]]:
        """
        Execute workflow

        Args:
            workflow_definition: Workflow definition (dict or JSON string)
            parameters: Workflow parameters
            stream: Whether to stream the response
            runner: Runner to use (uses default runner if not specified)

        Returns:
            For streaming: Generator yielding event data
            For non-streaming: Final response data

        Returns:
            Workflow execution
        """

        # Convert string to dict if needed
        if isinstance(workflow_definition, str):
            try:
                workflow_definition = json.loads(workflow_definition)
            except json.JSONDecodeError as e:
                error = WorkflowExecutionError(f"Invalid workflow JSON: {str(e)}")
                capture_exception(error)
                raise error

        # Add parameters if provided
        if parameters: workflow_definition["parameters"] = parameters

        # Use the runner from the workflow definition if specified, otherwise use default
        default_runner = workflow_definition.pop('runner', self.client.runner)

        # If a specific runner is provided, use it; otherwise, use the default
        if not runner: runner = default_runner

        # Prepare request body - workflow fields at top level
        request_body = {**workflow_definition}  # Spread workflow fields at top level

        endpoint = self._format_endpoint(Endpoints.WORKFLOW_EXECUTE, runner=runner)

        # Add native_sse=true for standard SSE format when streaming (same as standalone function)
        if stream:
            endpoint += "&native_sse=true"

        try:

            response = self._post(endpoint=endpoint, data=request_body, stream=stream)
            if stream:
                # Return the generator directly to make it iterable
                return response
            else:
                # For non-streaming, collect all data
                result = []
                for event in response:
                    result.append(event)
                return {"events": result}
        except Exception as e:
            error = WorkflowExecutionError(f"Error during workflow execution: {str(e)}")
            capture_exception(error)
            raise error

    def list(
        self,
        filter: str = "all",
        limit: int = 10,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        List workflow executions with filtering and pagination support.

        Args:
            filter: Filter workflows (all|running|completed|failed)
            limit: Limit number of results (default: 10)
            offset: Offset for pagination (default: 0)

        Returns:
            Dictionary containing:
            - workflows: List of workflow execution objects
            - pagination: Pagination information
            - success: Boolean indicating success
        """

        # Prepare request body
        request_body = {
            "filter": filter,
            "limit": limit,
            "offset": offset,
        }

        # Construct endpoint using the same pattern as execute
        endpoint = self._format_endpoint(Endpoints.WORKFLOW_LIST, runner=self.client.runner)

        # Make the POST request with stream=False to get direct response
        response = self._post(endpoint=endpoint, data=request_body, stream=False)

        # For non-streaming responses, response should be a requests.Response object
        # We need to get the JSON content directly
        if hasattr(response, 'json'):
            try:
                return response.json()
            except:
                # If JSON parsing fails, try to get text content
                return {"error": "Failed to parse response", "content": response.text}
        elif hasattr(response, '__iter__') and not isinstance(response, (str, bytes, dict)):
            # This is the problematic code - only for streaming responses
            # For list operations, this should not happen with stream=False
            result = []
            for event in response:
                result.append(event)
            return {"events": result}
        else:
            # Direct response (dict or other)
            return response
