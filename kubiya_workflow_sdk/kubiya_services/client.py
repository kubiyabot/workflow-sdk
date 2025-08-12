"""
Main client class for Kubiya SDK
"""
import json
import time
import requests
from typing import Optional, Dict, Any, Union, Generator
from urllib.parse import urljoin

from kubiya_workflow_sdk import __version__, capture_exception
from kubiya_workflow_sdk.core.exceptions import (
    APIError as KubiyaAPIError,
    WorkflowExecutionError,
    ConnectionError as KubiyaConnectionError,
    WorkflowTimeoutError as KubiyaTimeoutError,
    AuthenticationError as KubiyaAuthenticationError
)

from requests.adapters import HTTPAdapter
from urllib3 import Retry


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
            IntegrationService
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
                            workflow_ended = True
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
                yield json.loads(line)

        except Exception as e:
            error = WorkflowExecutionError(f"Error processing stream: {str(e)}")
            capture_exception(error)
            raise error
        finally:
            response.close()
