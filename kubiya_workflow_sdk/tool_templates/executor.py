"""Tool execution framework for Kubiya Workflow SDK."""

import asyncio
import logging
import os
from typing import Dict, Any, Optional, List, Union, Tuple
from datetime import datetime
import aiohttp
import requests
from dataclasses import dataclass, asdict

from kubiya_workflow_sdk.core import (
    ToolDefinition,
    AuthType,
    DEFAULT_API_URL,
    DEFAULT_RUNNER,
    TOOL_EXEC_TIMEOUT,
)

# Optional Sentry integration
try:
    from kubiya_workflow_sdk.core.sentry_config import (
        capture_exception,
        add_breadcrumb,
    )
except ImportError:
    # Fallback no-op functions if Sentry not available
    capture_exception = lambda *args, **kwargs: None
    add_breadcrumb = lambda *args, **kwargs: None

logger = logging.getLogger(__name__)


@dataclass
class ToolExecutionRequest:
    """Request to execute a tool."""

    tool_name: str
    tool_def: Optional[ToolDefinition] = None
    args: Dict[str, Any] = None
    runner: str = DEFAULT_RUNNER
    timeout: int = TOOL_EXEC_TIMEOUT

    def to_dict(self) -> Dict[str, Any]:
        """Convert to API format."""
        result = {
            "tool_name": self.tool_name,
        }

        if self.tool_def:
            result["tool_def"] = self.tool_def.to_dict()

        if self.args:
            result["args"] = self.args

        return result


@dataclass
class ToolExecutionResult:
    """Result of tool execution."""

    tool_name: str
    success: bool
    output: str
    error: Optional[str] = None
    exit_code: Optional[int] = None
    start_time: datetime = None
    end_time: datetime = None
    duration_seconds: float = None
    metadata: Dict[str, Any] = None


class ToolExecutor:
    """Execute tool_templates on Kubiya runners."""

    def __init__(
        self,
        api_token: Optional[str] = None,
        base_url: str = DEFAULT_API_URL,
        runner: str = DEFAULT_RUNNER,
        timeout: int = TOOL_EXEC_TIMEOUT,
    ):
        self.api_token = api_token or os.getenv("KUBIYA_API_KEY") or os.getenv("KUBIYA_API_TOKEN")
        if not self.api_token:
            raise ValueError("API token required. Set KUBIYA_API_KEY or pass api_token")

        self.base_url = base_url
        self.runner = runner
        self.timeout = timeout
        self.auth_type = AuthType.API_KEY

        # Setup session
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"{self.auth_type.value} {self.api_token}",
                "Content-Type": "application/json",
            }
        )

    def execute(
        self,
        tool_name: str,
        tool_def: Optional[Union[ToolDefinition, Dict[str, Any]]] = None,
        args: Optional[Dict[str, Any]] = None,
        runner: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> ToolExecutionResult:
        """Execute a tool synchronously.

        Args:
            tool_name: Name of the tool
            tool_def: Tool definition (if not pre-registered)
            args: Tool arguments
            runner: Override default runner
            timeout: Override default timeout

        Returns:
            ToolExecutionResult
        """
        # Convert tool_def if needed
        if isinstance(tool_def, dict):
            tool_def = ToolDefinition(**tool_def)

        # Create request
        request = ToolExecutionRequest(
            tool_name=tool_name,
            tool_def=tool_def,
            args=args or {},
            runner=runner or self.runner,
            timeout=timeout or self.timeout,
        )

        # Execute
        return self._execute_request(request)

    def execute_batch(
        self, requests: List[ToolExecutionRequest], max_concurrent: int = 5
    ) -> List[ToolExecutionResult]:
        """Execute multiple tool_templates concurrently.

        Args:
            requests: List of tool execution requests
            max_concurrent: Maximum concurrent executions

        Returns:
            List of results in same order as requests
        """
        # Use thread pool for concurrent requests
        from concurrent.futures import ThreadPoolExecutor, as_completed

        results = [None] * len(requests)

        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            # Submit all tasks
            future_to_index = {
                executor.submit(self._execute_request, req): i for i, req in enumerate(requests)
            }

            # Collect results
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    results[index] = future.result()
                except Exception as e:
                    results[index] = ToolExecutionResult(
                        tool_name=requests[index].tool_name, success=False, output="", error=str(e)
                    )

        return results

    def _execute_request(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """Execute a single tool request."""
        start_time = datetime.now()

        try:
            # API endpoint
            url = f"{self.base_url}/api/v1/tool_templates/exec"
            params = {"runner": request.runner}

            # Make request
            response = self.session.post(
                url, params=params, json=request.to_dict(), timeout=request.timeout
            )

            response.raise_for_status()

            # Parse response
            data = response.json()

            end_time = datetime.now()

            return ToolExecutionResult(
                tool_name=request.tool_name,
                success=data.get("success", False),
                output=data.get("output", ""),
                error=data.get("error"),
                exit_code=data.get("exit_code"),
                start_time=start_time,
                end_time=end_time,
                duration_seconds=(end_time - start_time).total_seconds(),
                metadata=data.get("metadata", {}),
            )

        except requests.exceptions.Timeout:
            end_time = datetime.now()
            return ToolExecutionResult(
                tool_name=request.tool_name,
                success=False,
                output="",
                error="Tool execution timeout",
                start_time=start_time,
                end_time=end_time,
                duration_seconds=(end_time - start_time).total_seconds(),
            )

        except Exception as e:
            end_time = datetime.now()
            return ToolExecutionResult(
                tool_name=request.tool_name,
                success=False,
                output="",
                error=str(e),
                start_time=start_time,
                end_time=end_time,
                duration_seconds=(end_time - start_time).total_seconds(),
            )

    def create_tool(self, name: str, description: str, type: str, **kwargs) -> ToolDefinition:
        """Create a tool definition.

        Args:
            name: Tool name
            description: Tool description
            type: Tool type (docker, python, shell, etc.)
            **kwargs: Additional tool configuration

        Returns:
            ToolDefinition
        """
        return ToolDefinition(name=name, description=description, type=type, **kwargs)

    def validate_tool(self, tool_def: ToolDefinition) -> List[str]:
        """Validate a tool definition.

        Args:
            tool_def: Tool definition to validate

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Required fields
        if not tool_def.name:
            errors.append("Tool name is required")
        if not tool_def.description:
            errors.append("Tool description is required")
        if not tool_def.type:
            errors.append("Tool type is required")

        # Type-specific validation
        if tool_def.type == "docker":
            if not tool_def.image:
                errors.append("Docker image is required for docker tool_templates")
        elif tool_def.type == "python":
            if not tool_def.content:
                errors.append("Python content is required for python tool_templates")
        elif tool_def.type == "shell":
            if not tool_def.content and not tool_def.command:
                errors.append("Shell content or command is required for shell tool_templates")

        return errors


class AsyncToolExecutor:
    """Async tool executor for high-performance operations."""

    def __init__(
        self,
        api_token: Optional[str] = None,
        base_url: str = DEFAULT_API_URL,
        runner: str = DEFAULT_RUNNER,
        timeout: int = TOOL_EXEC_TIMEOUT,
    ):
        self.api_token = api_token or os.getenv("KUBIYA_API_KEY") or os.getenv("KUBIYA_API_TOKEN")
        if not self.api_token:
            raise ValueError("API token required")

        self.base_url = base_url
        self.runner = runner
        self.timeout = timeout
        self.auth_type = AuthType.API_KEY
        self.headers = {
            "Authorization": f"{self.auth_type.value} {self.api_token}",
            "Content-Type": "application/json",
        }

    async def execute(
        self,
        tool_name: str,
        tool_def: Optional[Union[ToolDefinition, Dict[str, Any]]] = None,
        args: Optional[Dict[str, Any]] = None,
        runner: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> ToolExecutionResult:
        """Execute a tool asynchronously."""
        # Convert tool_def if needed
        if isinstance(tool_def, dict):
            tool_def = ToolDefinition(**tool_def)

        # Create request
        request = ToolExecutionRequest(
            tool_name=tool_name,
            tool_def=tool_def,
            args=args or {},
            runner=runner or self.runner,
            timeout=timeout or self.timeout,
        )

        # Execute
        return await self._execute_request(request)

    async def execute_batch(
        self, requests: List[ToolExecutionRequest], max_concurrent: int = 10
    ) -> List[ToolExecutionResult]:
        """Execute multiple tool_templates concurrently."""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def execute_with_limit(request):
            async with semaphore:
                return await self._execute_request(request)

        tasks = [execute_with_limit(req) for req in requests]
        return await asyncio.gather(*tasks, return_exceptions=True)

    async def _execute_request(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """Execute a single tool request asynchronously."""
        start_time = datetime.now()

        # Add a breadcrumb for tool execution start
        add_breadcrumb(
            crumb={"message": "Starting async tool execution", "category": "tool_execution"},
            hint={"category": "tool_execution"},
            data={
                "tool_name": request.tool_name,
                "runner": request.runner,
                "timeout": request.timeout
            }
        )

        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/v1/tool_templates/exec"
                params = {"runner": request.runner}

                async with session.post(
                    url,
                    params=params,
                    json=request.to_dict(),
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=request.timeout),
                ) as response:
                    response.raise_for_status()
                    data = await response.json()

                    end_time = datetime.now()

                    return ToolExecutionResult(
                        tool_name=request.tool_name,
                        success=data.get("success", False),
                        output=data.get("output", ""),
                        error=data.get("error"),
                        exit_code=data.get("exit_code"),
                        start_time=start_time,
                        end_time=end_time,
                        duration_seconds=(end_time - start_time).total_seconds(),
                        metadata=data.get("metadata", {}),
                    )

        except asyncio.TimeoutError:
            end_time = datetime.now()
            error_result = ToolExecutionResult(
                tool_name=request.tool_name,
                success=False,
                output="",
                error="Tool execution timeout",
                start_time=start_time,
                end_time=end_time,
                duration_seconds=(end_time - start_time).total_seconds(),
            )
            
            # Capture timeout error to Sentry
            timeout_error = asyncio.TimeoutError(f"Async tool execution timeout for {request.tool_name}")
            capture_exception(timeout_error, extra=asdict(error_result))
            
            return error_result

        except Exception as e:
            end_time = datetime.now()
            error_result = ToolExecutionResult(
                tool_name=request.tool_name,
                success=False,
                output="",
                error=str(e),
                start_time=start_time,
                end_time=end_time,
                duration_seconds=(end_time - start_time).total_seconds(),
            )

            # Capture execution error to Sentry
            capture_exception(e, extra=asdict(error_result))

            return error_result


# Convenience functions
def execute_tool(
    tool_name: str,
    tool_def: Optional[Union[ToolDefinition, Dict[str, Any]]] = None,
    args: Optional[Dict[str, Any]] = None,
    api_token: Optional[str] = None,
    **kwargs,
) -> ToolExecutionResult:
    """Execute a tool synchronously.

    Args:
        tool_name: Name of the tool
        tool_def: Tool definition (if not pre-registered)
        args: Tool arguments
        api_token: Override API token
        **kwargs: Additional executor options

    Returns:
        ToolExecutionResult
    """
    executor = ToolExecutor(api_token=api_token, **kwargs)
    return executor.execute(tool_name, tool_def, args)


async def execute_tool_async(
    tool_name: str,
    tool_def: Optional[Union[ToolDefinition, Dict[str, Any]]] = None,
    args: Optional[Dict[str, Any]] = None,
    api_token: Optional[str] = None,
    **kwargs,
) -> ToolExecutionResult:
    """Execute a tool asynchronously.

    Args:
        tool_name: Name of the tool
        tool_def: Tool definition (if not pre-registered)
        args: Tool arguments
        api_token: Override API token
        **kwargs: Additional executor options

    Returns:
        ToolExecutionResult
    """
    executor = AsyncToolExecutor(api_token=api_token, **kwargs)
    return await executor.execute(tool_name, tool_def, args)
