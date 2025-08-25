"""Kubiya API client for workflow operations."""

import json
import time
import logging
import asyncio
import aiohttp
from typing import Dict, Any, Optional, Generator, Union, AsyncGenerator, List
from urllib.parse import urljoin
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from .__version__ import __version__
from kubiya_workflow_sdk.core.constants import WorkflowStatus
from kubiya_workflow_sdk.core.exceptions import (
    APIError as KubiyaAPIError,
    WorkflowExecutionError,
    ConnectionError as KubiyaConnectionError,
    WorkflowTimeoutError as KubiyaTimeoutError,
    AuthenticationError as KubiyaAuthenticationError,
    WorkflowError as WorkflowNotFoundError,
)

# Optional Sentry integration
try:
    from kubiya_workflow_sdk.core.sentry_config import (
        capture_exception,
        capture_message,
        add_breadcrumb,
        set_workflow_context,
    )
except ImportError:
    # Fallback no-op functions if Sentry not available
    capture_exception = lambda *args, **kwargs: None
    capture_message = lambda *args, **kwargs: None
    add_breadcrumb = lambda *args, **kwargs: None
    set_user_context = lambda *args, **kwargs: None
    set_workflow_context = lambda *args, **kwargs: None

logger = logging.getLogger(__name__)


class StreamingKubiyaClient:
    """Async streaming client for real-time workflow execution with the Kubiya API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.kubiya.ai",
        runner: str = "kubiya-hosted",
        timeout: int = 300,
        max_retries: int = 3,
        max_connections: int = 30,
        max_connections_per_host: int = 30,
        org_name: Optional[str] = None
    ):
        """Initialize the streaming Kubiya client.

        Args:
            api_key: Kubiya API key
            base_url: Base URL for the Kubiya API
            runner: Kubiya runner instance name
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            max_connections: # Maximum total simultaneous connections for aiohttp session
            max_connections_per_host: Maximum simultaneous connections per host
            org_name: Organization name for API calls
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.runner = runner
        self.timeout = timeout
        self.max_retries = max_retries
        self.max_connections = max_connections
        self.max_connections_per_host = max_connections_per_host
        self.org_name = org_name

        self._connector = None
        self._session = None

        # Default headers - Use UserKey format for API key authentication
        self.headers = {
            "Authorization": f"UserKey {api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "User-Agent": f"kubiya_workflow_sdk@{__version__}"
        }

    async def __aenter__(self):
        # Create a connector with connection pooling
        self._connector = aiohttp.TCPConnector(
            limit=self.max_connections,
            limit_per_host=self.max_connections_per_host,
            ttl_dns_cache=300,  # 5 minutes DNS cache
            use_dns_cache=True,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )

        # Create timeout configuration
        timeout = aiohttp.ClientTimeout(
            total=self.timeout,
            connect=30,  # 30 seconds to connect
            sock_read=60  # 60 seconds to read data
        )

        # Create session
        self._session = aiohttp.ClientSession(
            connector=self._connector,
            timeout=timeout,
            headers=self.headers,
            raise_for_status=False  # Handle status codes manually
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close session and cleanup resources with proper error handling."""

        if self._session is not None:
            try:
                if not self._session.closed:
                    await self._session.close()
            except Exception:
                pass  # Ignore errors during cleanup
            finally:
                self._session = None

            # Close connector
        if self._connector is not None:
            try:
                if not self._connector.closed:
                    await self._connector.close()
            except Exception:
                pass  # Ignore errors during cleanup
            finally:
                self._connector = None

    async def execute_workflow_stream(
        self, workflow: Dict[str, Any], params: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute a workflow with async streaming.

        Args:
            workflow: Workflow definition dictionary
            params: Workflow parameters

        Yields:
            Event dictionaries from the streaming response

        Raises:
            WorkflowExecutionError: If execution fails
            KubiyaAPIError: For API errors
        """
        # Use the runner from the workflow definition if specified, otherwise use default
        runner = workflow.pop('runner', self.runner)
        # Prepare request body - workflow fields at top level
        request_body = {**workflow}  # Spread workflow fields at top level

        if params:
            request_body["parameters"] = params

        # Execute the workflow
        url = urljoin(self.base_url, f"/api/v1/workflow?runner={runner}&operation=execute_workflow&native_sse=true")

        # Add breadcrumb for workflow execution start
        add_breadcrumb(
            crumb={"message": "Execute workflow async", "category": "workflow_execution"},
            hint={"category": "workflow_execution"},
            data={"workflow_name": workflow.get("name"), "runner": runner}
        )

        try:
            async with self._session.post(url, json=request_body) as response:
                # Check for authentication errors
                if response.status == 401:
                    error = KubiyaAuthenticationError("Invalid API token or unauthorized access")
                    capture_exception(error, extra={"api_url": str(response.url), "status_code": response.status})
                    raise error

                # Check for other errors
                if response.status >= 400:
                    error_text = await response.text()
                    logger.error(f"API Error Response: {error_text}")
                    error = KubiyaAPIError(
                        f"API request failed: HTTP {response.status} - {error_text[:200]}",
                        status_code=response.status,
                        response_body=error_text,
                    )
                    capture_exception(error, extra={
                        "request_body": request_body,
                        "api_url": str(response.url),
                        "status_code": response.status,
                        "response_body": error_text
                    })
                    raise error

                try:
                    # Process the streaming response
                    async for line in response.content:
                        line = line.decode("utf-8").strip()

                        if line.startswith("data: "):
                            data = line[6:]  # Remove 'data: ' prefix

                            if data.strip() == "[DONE]":
                                break

                            try:
                                event_data = json.loads(data)
                                yield event_data

                                # Check for end events
                                if event_data.get("end") or event_data.get("finishReason"):
                                    break

                            except json.JSONDecodeError:
                                # Yield raw data if it's not JSON
                                yield {"type": "raw_data", "data": data}

                        elif line.startswith("event: "):
                            event_type = line[7:].strip()
                            if event_type in ["end", "error"]:
                                if event_type == "error":
                                    error = WorkflowExecutionError("Streaming execution failed")
                                    try:
                                        error_data = json.loads(data)
                                    except json.JSONDecodeError:
                                        error_data = {"raw_data": data}
                                    capture_exception(error, extra=error_data)
                                yield {"type": "event", "event_type": event_type}
                                if event_type == "end":
                                    break
                except Exception as e:
                    error = WorkflowExecutionError(f"Streaming execution failed: {str(e)}")
                    capture_exception(error, extra={"workflow_name": workflow.get("name"), "runner": runner})
                    raise error


        except aiohttp.ClientError as e:
            error = KubiyaConnectionError(f"Failed to connect to Kubiya API: {str(e)}")
            capture_exception(error, extra={"api_url": url, "runner": runner})
            raise error
        except asyncio.TimeoutError:
            error = KubiyaTimeoutError(f"Request timed out after {self.timeout} seconds")
            capture_exception(error, extra={"timeout": self.timeout, "api_url": url})
            raise error
        except Exception as e:
            if not isinstance(
                e, (KubiyaAPIError, KubiyaAuthenticationError, KubiyaConnectionError, WorkflowExecutionError)
            ):
                error = WorkflowExecutionError(f"Streaming execution failed: {str(e)}")
                capture_exception(error, extra={"workflow_name": workflow.get("name"), "runner": runner})
                raise error
            raise


class KubiyaClient:
    """
    Main client for interacting with Kubiya API

    This client provides access to all Kubiya platform functionality including
    agents, workflows, tools, integrations, and more.

    Example:
        # Initialize with API key
        client = KubiyaClient(api_key="your-api-key")

        # Initialize with custom config.
        config = KubiyaConfig(
            api_key="your-api-key",
            base_url="https://custom.kubiya.ai",
            timeout=60
        )
        client = KubiyaClient(config=config)
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.kubiya.ai",
        runner: str = "kubiya-hosted",
        timeout: int = 300,
        max_retries: int = 3,
        org_name: Optional[str] = None,
    ):
        """
        Initialize Kubiya client

        Args:
            api_key: Kubiya API key
            base_url: Base URL for the Kubiya API
            runner: Kubiya runner instance name
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            org_name: Organization name for API calls

        Raises:
            ConfigurationError: If configuration is invalid
            AuthenticationError: If authentication setup fails
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.runner = runner
        self.timeout = timeout
        self.org_name = org_name

        # Create session with retry logic
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set default headers - Use UserKey format for API key authentication
        self.session.headers.update({
            "Authorization": f"UserKey {api_key}",
            "Content-Type": "application/json",
            "User-Agent": f"kubiya_workflow_sdk@{__version__}"
        })

        # Initialize all services
        from kubiya_workflow_sdk.kubiya_services.services import (
            WorkflowService,
            WebhookService,
            UserService,
            TriggerService,
            ToolService,
            SourceService,
            SecretService,
            RunnerService,
            ProjectService,
            PolicyService,
            KnowledgeService,
            IntegrationService,
            DocumentationService,
            AuditService,
            AgentService,
            StacksService,
        )

        self.workflows = WorkflowService(self)
        self.webhooks = WebhookService(self)
        self.users = UserService(self)
        self.triggers = TriggerService(self)
        self.tools = ToolService(self)
        self.sources = SourceService(self)
        self.secrets = SecretService(self)
        self.runners = RunnerService(self)
        self.projects = ProjectService(self)
        self.policies = PolicyService(self)
        self.knowledge = KnowledgeService(self)
        self.integrations = IntegrationService(self)
        self.documentations = DocumentationService(self)
        self.audit = AuditService(self)
        self.agents = AgentService(self)
        self.stacks = StacksService(self)

    def make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        base_url: Optional[str] = None,
        **kwargs,
    ) -> Union[requests.Response, Generator[str, None, None]]:
        """Make an HTTP request to the Kubiya API.

        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request data
            stream: Whether to stream the response
            base_url: Base URL for API request. If None, uses the client's base URL.
            **kwargs: Additional request arguments

        Returns:
            Response object or generator for streaming responses

        Raises:
            KubiyaAPIError: For API errors
            KubiyaConnectionError: For connection errors
            KubiyaTimeoutError: For timeout errors
            KubiyaAuthenticationError: For authentication errors
        """
        # If no base URL is provided, use the default one.
        base_url = base_url or self.base_url
        url = urljoin(base_url, endpoint)

        # Update headers for streaming if needed
        headers = kwargs.pop("headers", {})
        if stream:
            headers["Accept"] = "text/event-stream"

        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                timeout=self.timeout,
                stream=stream,
                headers=headers,
                **kwargs,
            )

            # Check for authentication errors
            if response.status_code == 401:
                error = KubiyaAuthenticationError("Invalid API token or unauthorized access")
                capture_exception(error, extra={"api_url": str(response.url), "status_code": response.status_code})
                raise error

            # For non-streaming responses, check status
            if not stream:
                try:
                    response.raise_for_status()
                except requests.HTTPError as e:
                    error_data = {}
                    try:
                        error_data = response.json()
                    except:
                        pass
                    error = KubiyaAPIError(
                        f"API request failed: {e} {error_data}",
                        status_code=response.status_code,
                        response_body=json.dumps(error_data) if error_data else None,
                    )
                    capture_exception(error, extra={
                        "request_body": data,
                        "api_url": url,
                        "status_code": response.status_code,
                        "response_body": error_data
                    })
                    raise error
            else:
                return self._handle_stream(response)
            return response

        except requests.exceptions.Timeout:
            error = KubiyaTimeoutError(f"Request timed out after {self.timeout} seconds")
            capture_exception(error, extra={"timeout": self.timeout, "api_url": url})
            raise error
        except requests.exceptions.ConnectionError as e:
            error = KubiyaConnectionError(f"Failed to connect to Kubiya API: {str(e)}")
            capture_exception(error, extra={"api_url": url})
            raise error
        except requests.exceptions.RequestException as e:
            if not isinstance(e, (KubiyaAPIError, KubiyaAuthenticationError)):
                error = KubiyaAPIError(f"Request failed: {str(e)}")
                capture_exception(error)
                raise error
            raise

    def _handle_stream(self, response: requests.Response) -> Generator[str, None, None]:
        """Handle Server-Sent Events (SSE) stream with proper heartbeat handling.

        Args:
            response: Streaming response object

        Yields:
            Event data strings

        Raises:
            WorkflowExecutionError: For execution errors in the stream
        """
        try:
            workflow_ended = False

            for line in response.iter_lines():
                if line:
                    if isinstance(line, bytes):
                        line = line.decode("utf-8")

                    if line.startswith("data: "):
                        data = line[6:]  # Remove 'data: ' prefix
                        if data.strip() == "[DONE]":
                            return

                        # Handle Kubiya's custom format within SSE data
                        # Format is like "2:{json}" or "d:{json}"
                        if data and len(data) > 2 and data[1] == ":":
                            prefix = data[0]
                            json_data = data[2:]

                            try:
                                event_data = json.loads(json_data)

                                # Check for end events
                                if (
                                    prefix == "d"
                                    or event_data.get("end")
                                    or event_data.get("finishReason")
                                ):
                                    workflow_ended = True
                                elif event_data.get("type") == "heartbeat":
                                    last_heartbeat = time.time()

                                # Yield the parsed JSON data
                                yield json.dumps(event_data)
                            except json.JSONDecodeError:
                                # If it's not valid JSON, yield as is
                                yield data
                        else:
                            # Standard format, try to parse
                            try:
                                event_data = json.loads(data)
                                if event_data.get("end") or event_data.get("finishReason"):
                                    workflow_ended = True
                                elif event_data.get("type") == "heartbeat":
                                    last_heartbeat = time.time()
                            except json.JSONDecodeError:
                                pass

                            yield data

                        # If workflow ended, stop processing
                        if workflow_ended:
                            return

                elif line and line.startswith("retry:"):
                    # Handle SSE retry directive
                    yield line
                elif line and line.startswith("event:"):
                    # Handle SSE event type
                    event_type = line[6:].strip()
                    if event_type in ["end", "error"]:
                        yield line
                        # Don't immediately close on error events - wait for explicit end
                    else:
                        yield line
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    # If line is not valid JSON, yield it as a string
                    yield line

        except Exception as e:
            error = WorkflowExecutionError(f"Error processing stream: {str(e)}")
            capture_exception(error)
            raise error
        finally:
            response.close()

    def execute_workflow(
        self,
        workflow_definition: Union[Dict[str, Any], str],
        parameters: Optional[Dict[str, Any]] = None,
        stream: bool = True,
    ) -> Union[Dict[str, Any], Generator[str, None, None]]:
        """Execute a workflow.

        Args:
            workflow_definition: Workflow definition (dict or JSON string)
            parameters: Workflow parameters
            stream: Whether to stream the response

        Returns:
            For streaming: Generator yielding event data
            For non-streaming: Final response data

        Raises:
            WorkflowExecutionError: If execution fails
            KubiyaAPIError: For API errors
        """
        # Convert string to dict if needed
        if isinstance(workflow_definition, str):
            try:
                workflow_definition = json.loads(workflow_definition)
            except json.JSONDecodeError as e:
                error = WorkflowExecutionError(f"Invalid workflow JSON: {str(e)}")
                capture_exception(error)
                raise error

        # Ensure workflow_definition is properly formatted
        if not isinstance(workflow_definition, dict):
            error = WorkflowExecutionError("Workflow definition must be a dictionary")
            capture_exception(error)
            raise error

        # Add parameters if provided
        if parameters:
            workflow_definition["parameters"] = parameters

        # Use the runner from the workflow definition if specified, otherwise use default
        runner = workflow_definition.pop('runner', self.runner)
        # Prepare request body - workflow fields at top level
        request_body = {**workflow_definition}  # Spread workflow fields at top level

        logger.info("Executing workflow...")
        logger.debug(f"Request body: {json.dumps(request_body, indent=2)}")

        # Execute the workflow
        endpoint = f"/api/v1/workflow?runner={runner}&operation=execute_workflow"
        if stream:
            # Add native_sse=true for standard SSE format when streaming
            endpoint += "&native_sse=true"

        response = self.make_request(
            method="POST", endpoint=endpoint, data=request_body, stream=stream
        )

        if stream:
            return response
        else:
            # For non-streaming, collect all data
            result = []
            for event in response:
                result.append(event)
            return {"events": result}

    # ============= NEW PLATFORM CAPABILITIES =============

    def get_runners(self) -> List[Dict[str, Any]]:
        """Get available runners in the organization.

        Returns:
            List of runner configurations (without capabilities field)

        Raises:
            KubiyaAPIError: For API errors
        """
        response = self.make_request(method="GET", endpoint=f"/api/v1/runners")
        data = response.json()

        # Handle different response formats
        if isinstance(data, dict):
            # If it's a dict of runners, convert to list
            runners = []
            for runner_name, runner_info in data.items():
                runner_data = {"name": runner_name}
                if isinstance(runner_info, dict):
                    runner_data.update(runner_info)
                # Remove capabilities field if present
                runner_data.pop("capabilities", None)
                runners.append(runner_data)
            return runners
        elif isinstance(data, list):
            # Remove capabilities from each runner
            return [
                {k: v for k, v in runner.items() if k != "capabilities"}
                for runner in data
            ]
        else:
            error = KubiyaAPIError("Unexpected response format from get runners endpoint.")
            capture_exception(error, extra={"response": data})
            raise error

    def get_runner_health(self, runner_name: str) -> Dict[str, Any]:
        """Get health status of a specific runner.

        Args:
            runner_name: Name of the runner to check

        Returns:
            Health status including component versions and checks

        Raises:
            KubiyaAPIError: For API errors
        """
        response = self.make_request(
            method="GET", 
            endpoint=f"/api/v3/runners/{runner_name}/health"
        )
        return response.json()

    def get_runners_with_health(
        self, 
        check_health: bool = True,
        required_components: Optional[Dict[str, str]] = None,
        max_workers: int = 10,
        health_timeout: int = 5
    ) -> List[Dict[str, Any]]:
        """Get runners with their health status and filter by component versions.

        Args:
            check_health: Whether to check health status for each runner
            required_components: Dict of component names to required versions
                                e.g., {"agent-manager": "0.1.17", "tool-manager": None}
                                None value means any version is acceptable
            max_workers: Maximum number of parallel health check workers
            health_timeout: Timeout for each health check in seconds

        Returns:
            List of runners with health information

        Raises:
            KubiyaAPIError: For API errors
        """
        # Get base runner list
        runners = self.get_runners()
        
        if not check_health:
            # Return runners without capabilities field
            return [
                {k: v for k, v in runner.items() if k != 'capabilities'}
                for runner in runners
            ]
        
        # Check if we need to filter by components from environment
        env_components = {}
        if os.environ.get("KUBIYA_REQUIRED_AGENT_MANAGER_VERSION"):
            env_components["agent-manager"] = os.environ["KUBIYA_REQUIRED_AGENT_MANAGER_VERSION"]
        if os.environ.get("KUBIYA_REQUIRED_TOOL_MANAGER_VERSION"):
            env_components["tool-manager"] = os.environ["KUBIYA_REQUIRED_TOOL_MANAGER_VERSION"]
        
        # Merge with provided requirements
        if required_components:
            env_components.update(required_components)
        required_components = env_components if env_components else required_components
        
        # Function to check health for a single runner
        def check_runner_health(runner):
            runner_name = runner.get("name")
            if not runner_name:
                return runner
            
            # Create a copy without capabilities
            runner_copy = {k: v for k, v in runner.items() if k != 'capabilities'}
            
            try:
                # Use a separate session with timeout for health checks
                health_session = requests.Session()
                health_session.headers.update(self.session.headers)
                health_session.timeout = health_timeout
                
                # Get health status with retries
                retry_strategy = Retry(
                    total=3,
                    backoff_factor=0.5,
                    status_forcelist=[500, 502, 503, 504],
                    allowed_methods=["GET"]
                )
                adapter = HTTPAdapter(max_retries=retry_strategy)
                health_session.mount("http://", adapter)
                health_session.mount("https://", adapter)
                
                response = health_session.get(
                    urljoin(self.base_url, f"/api/v3/runners/{runner_name}/health"),
                    timeout=health_timeout
                )
                response.raise_for_status()
                health_data = response.json()
                
                runner_copy["health"] = health_data
                runner_copy["health_status"] = health_data.get("status", "unknown")
                runner_copy["is_healthy"] = health_data.get("health") == "true"
                
            except Exception as e:
                logger.warning(f"Failed to fetch health for runner {runner_name}: {e}")
                # Return error status if health check fails
                runner_copy["health"] = {
                    "health": "false",
                    "status": "error",
                    "error": str(e),
                    "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "checks": []
                }
                runner_copy["health_status"] = "error"
                runner_copy["is_healthy"] = False

                capture_exception(e, extra={"response": runner_copy})

            # Check component requirements if specified
            if required_components and runner_copy.get("is_healthy"):
                meets_requirements = True
                component_versions = {}
                
                for check in runner_copy.get("health", {}).get("checks", []):
                    component_name = check.get("name")
                    component_version = check.get("version")
                    component_status = check.get("status")
                    
                    if component_name:
                        component_versions[component_name] = {
                            "version": component_version,
                            "status": component_status,
                            "metadata": check.get("metadata", {})
                        }
                    
                    # Check if this component has a requirement
                    if component_name in required_components:
                        required_version = required_components[component_name]
                        
                        # Component must be healthy
                        if component_status != "ok":
                            meets_requirements = False
                            break
                        
                        # Check version if specified
                        if required_version and component_version != required_version:
                            meets_requirements = False
                            break
                
                runner_copy["component_versions"] = component_versions
                runner_copy["meets_requirements"] = meets_requirements
            else:
                runner_copy["meets_requirements"] = not required_components
            
            return runner_copy
        
        # Use ThreadPoolExecutor for parallel health checks
        enriched_runners = []
        
        with ThreadPoolExecutor(max_workers=min(max_workers, len(runners))) as executor:
            # Submit all health check tasks
            future_to_runner = {
                executor.submit(check_runner_health, runner): runner 
                for runner in runners
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_runner):
                try:
                    result = future.result()
                    enriched_runners.append(result)
                except Exception as e:
                    # If a health check fails catastrophically, include the runner anyway
                    runner = future_to_runner[future]
                    logger.error(f"Critical error checking runner {runner.get('name')}: {e}")
                    runner_copy = {k: v for k, v in runner.items() if k != 'capabilities'}
                    runner_copy.update({
                        "health_status": "error",
                        "is_healthy": False,
                        "meets_requirements": False,
                        "health": {"error": str(e)}
                    })
                    enriched_runners.append(runner_copy)

                    capture_exception(e, extra={"response": runner_copy})
        
        # Sort by name for consistent ordering
        enriched_runners.sort(key=lambda r: r.get("name", ""))
        
        return enriched_runners

    def get_integrations(self) -> List[Dict[str, Any]]:
        """Get available integrations in the organization.

        Returns:
            List of integration configurations

        Raises:
            KubiyaAPIError: For API errors
        """
        response = self.make_request(method="GET", endpoint="/api/v2/integrations", params={"full": "true"})
        data = response.json()

        # Handle different response formats
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "integrations" in data:
            return data["integrations"]
        else:
            error = KubiyaAPIError("Unexpected response format from integrations endpoint")
            capture_exception(error, extra={"response": data})
            raise error

    def list_secrets(self) -> List[Dict[str, Any]]:
        """List available secrets in the organization.

        Returns:
            List of secrets (without values)

        Raises:
            KubiyaAPIError: For API errors
        """
        response = self.make_request(method="GET", endpoint="/api/v2/secrets")
        data = response.json()

        # Handle different response formats
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "secrets" in data:
            return data["secrets"]
        else:
            error = KubiyaAPIError("Unexpected response format from secrets endpoint")
            capture_exception(error, extra={"response": data})
            raise error

    def get_secrets_metadata(self) -> List[Dict[str, Any]]:
        """Get metadata about available secrets (names only, not values).

        Uses the /api/v1/secrets endpoint to list secrets.

        Returns:
            List of secret metadata

        Raises:
            KubiyaAPIError: For API errors
        """
        response = self.make_request(method="GET", endpoint="/api/v1/secrets")
        data = response.json()

        # Handle different response formats
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "secrets" in data:
            return data["secrets"]
        else:
            error = KubiyaAPIError("Unexpected response format from secrets endpoint")
            capture_exception(error, extra={"response": data})
            raise error

    def get_organization_info(self) -> Dict[str, Any]:
        """Get organization information.

        NOTE: Currently returns the org_name provided during initialization,
        as there is no dedicated API endpoint for organization info.

        Returns:
            Organization details
        """
        # Return the org_name provided during initialization
        # In the future, this could be expanded when an API endpoint is available
        return {
            "id": self.org_name or "default",
            "name": self.org_name or "default",
            "plan": "enterprise",  # Default plan type
        }

    async def execute_workflow_stream(
        self, workflow_definition: Dict[str, Any], parameters: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute a workflow and stream results asynchronously.
        
        This is a wrapper that creates a StreamingKubiyaClient and executes the workflow.
        
        Args:
            workflow_definition: Workflow definition dict
            parameters: Workflow parameters
            
        Yields:
            Workflow execution events
        """
        # Create streaming client with same config
        streaming_client = StreamingKubiyaClient(
            api_key=self.session.headers.get("Authorization", "").replace("UserKey ", ""),
            base_url=self.base_url,
            runner=self.runner,
            timeout=self.timeout,
            max_retries=3,  # Use default value since we don't store max_retries
            org_name=self.org_name
        )
        
        # Execute and stream
        async for event in streaming_client.execute_workflow_stream(workflow_definition, parameters):
            yield event

    def create_agent(
        self,
        name: str,
        description: str,
        system_message: str,
        tools: Optional[List[str]] = None,
        model: str = "together_ai/deepseek-ai/DeepSeek-V3",
        **kwargs,
    ) -> Dict[str, Any]:
        """Create a new agent in the Kubiya platform.

        Args:
            name: Agent name
            description: Agent description
            system_message: System prompt for the agent
            tools: List of tool names to enable
            model: LLM model to use
            **kwargs: Additional agent configuration

        Returns:
            Created agent details

        Raises:
            KubiyaAPIError: For API errors
        """
        agent_data = {
            "name": name,
            "description": description,
            "system_message": system_message,
            "tools": tools or [],
            "model": model,
            **kwargs,
        }

        response = self.make_request(method="POST", endpoint="/api/v1/agents", data=agent_data)
        return response.json()

    def list_agents(
        self, limit: int = 100, offset: int = 0, search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List available agents.

        Args:
            limit: Maximum number of results
            offset: Result offset for pagination
            search: Search term for filtering

        Returns:
            List of agents

        Raises:
            KubiyaAPIError: For API errors
        """
        params = {"limit": limit, "offset": offset}
        if search:
            params["search"] = search

        response = self.make_request(method="GET", endpoint="/api/v1/agents", params=params)
        data = response.json()

        # Handle different response formats
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "agents" in data:
            return data["agents"]
        else:
            error = KubiyaAPIError("Unexpected response format from agents endpoint")
            capture_exception(error, extra={"response": data})
            raise error

    def execute_agent(
        self,
        agent_id: str,
        prompt: str,
        session_id: Optional[str] = None,
        stream: bool = True,
        **kwargs,
    ) -> Union[Dict[str, Any], Generator[str, None, None]]:
        """Execute an agent with a prompt.

        Args:
            agent_id: Agent UUID
            prompt: User prompt
            session_id: Session ID for conversation continuity
            stream: Whether to stream the response
            **kwargs: Additional execution parameters

        Returns:
            For streaming: Generator yielding event data
            For non-streaming: Final response data

        Raises:
            KubiyaAPIError: For API errors
        """
        execution_data = {"prompt": prompt, "session_id": session_id, **kwargs}

        response = self.make_request(
            method="POST",
            endpoint=f"/api/v1/agents/{agent_id}/execute",
            data=execution_data,
            stream=stream,
        )

        if stream:
            return response
        else:
            return response.json()


# Convenience function for simple workflow execution
def execute_workflow(
    workflow_definition: Union[Dict[str, Any], str],
    api_key: str,
    parameters: Optional[Dict[str, Any]] = None,
    base_url: str = "https://api.kubiya.ai",
    runner: str = "kubiya-hosted",
    stream: bool = True,
) -> Union[Dict[str, Any], Generator[str, None, None]]:
    """Execute a workflow using the Kubiya API.

    This is a convenience function that creates a client and executes the workflow.

    Args:
        workflow_definition: Workflow definition (dict or JSON string)
        api_key: Kubiya API key
        parameters: Workflow parameters
        base_url: Base URL for the Kubiya API
        runner: Kubiya runner instance name
        stream: Whether to stream the response

    Returns:
        For streaming: Generator yielding event data
        For non-streaming: Final response data

    Example:
        >>> from kubiya_workflow_sdk import execute_workflow
        >>> # Stream workflow execution
        >>> for event in execute_workflow(workflow_def, api_key="your-key"):
        ...     print(event)
    """
    client = KubiyaClient(api_key=api_key, base_url=base_url, runner=runner)

    return client.execute_workflow(
        workflow_definition=workflow_definition, parameters=parameters, stream=stream
    )
