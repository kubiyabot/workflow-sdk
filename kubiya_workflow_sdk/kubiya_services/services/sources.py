"""
Source service for managing sources
"""
import concurrent
import json
import logging
import os
import sys
import threading
import urllib.parse
from datetime import datetime

from typing import Optional, Dict, Any, List, Union

from kubiya_workflow_sdk import capture_exception
from kubiya_workflow_sdk.kubiya_services.constants import Endpoints
from kubiya_workflow_sdk.kubiya_services.exceptions import SourceError, SourceNotFoundError, SourceValidationError
from kubiya_workflow_sdk.kubiya_services.services.base import BaseService

logger = logging.getLogger(__name__)

class _InlineService(BaseService):
    def add(
        self,
        source_uuid: str,
        file: Optional[str] = None,
        url: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        type: str = "docker",
        image: Optional[str] = None,
        content: Optional[str] = None,
        arg: Optional[List[str]] = None,
        env: Optional[List[str]] = None,
        editor: bool = False,
    ) -> Dict[str, Any]:
        """Add a tool to an inline source.

        Accepts tool from file, URL, or parameters. Editor-based creation is not supported here.
        """
        try:
            # Load current source
            source = self._get(self._format_endpoint(Endpoints.SOURCE_METADATA, source_uuid=source_uuid))
            if not isinstance(source, dict):
                raise SourceNotFoundError("failed to get source")

            new_tool: Optional[Dict[str, Any]] = None

            if editor:
                raise SourceError("editor-based tool creation is not supported in service context")
            elif file:
                new_tool = self._parse_tool_file(file)
            elif url:
                new_tool = self._load_tool_from_url(url)
            elif name and content is not None:
                new_tool = {
                    "name": name,
                    "description": description or "",
                    "type": type,
                    "image": image or "",
                    "content": content,
                }
                if arg:
                    tool_args: List[Dict[str, Any]] = []
                    for a in arg:
                        parts = a.split(":", 3)
                        if len(parts) >= 3:
                            tool_args.append({
                                "name": parts[0],
                                "type": parts[1],
                                "description": parts[2],
                                "required": len(parts) > 3 and parts[3] == "true",
                            })
                    if tool_args:
                        new_tool["args"] = tool_args
                if env:
                    new_tool["env"] = env
            else:
                raise SourceValidationError("must specify --editor, --file, --url, or provide --name and --content")

            inline_tools = list(source.get("inline_tools", []))
            inline_tools.append(new_tool)

            payload = {
                "inline_tools": inline_tools,
                "type": "inline",
            }
            endpoint = self._format_endpoint(Endpoints.SOURCE_GET, source_uuid=source_uuid)
            updated = self._put(endpoint=endpoint, data=payload).json()
            return updated if isinstance(updated, dict) else {"result": updated}
        except Exception as e:
            raise SourceError(f"Failed to add inline tool: {e}")

    def delete(
        self,
        source_uuid: str,
        tool_name: str,
    ) -> Dict[str, Any]:
        """Delete a tool from an inline source by name."""
        try:
            source = self._get(self._format_endpoint(Endpoints.SOURCE_METADATA, source_uuid=source_uuid))
            if not isinstance(source, dict):
                raise SourceNotFoundError("failed to get source")

            tools = list(source.get("inline_tools", []))
            new_tools: List[Dict[str, Any]] = [t for t in tools if t.get("name") != tool_name]
            if len(new_tools) == len(tools):
                raise SourceValidationError(f"tool '{tool_name}' not found in source")

            payload = {
                "inline_tools": new_tools,
                "type": "inline",
            }
            endpoint = self._format_endpoint(Endpoints.SOURCE_GET, source_uuid=source_uuid)
            updated = self._put(endpoint=endpoint, data=payload).json()
            return updated if isinstance(updated, dict) else {"result": updated}
        except Exception as e:
            raise SourceError(f"Failed to delete inline tool: {e}")

    def update(
        self,
        source_uuid: str,
        tool_name: str,
        file: Optional[str] = None,
        url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update a specific tool in an inline source from file or URL."""
        try:
            if not file and not url:
                raise SourceValidationError("must specify --file or --url")

            source = self._get(self._format_endpoint(Endpoints.SOURCE_METADATA, source_uuid=source_uuid))
            if not isinstance(source, dict):
                raise SourceNotFoundError("failed to get source")

            tools = list(source.get("inline_tools", []))
            idx = next((i for i, t in enumerate(tools) if t.get("name") == tool_name), -1)
            if idx == -1:
                raise SourceValidationError(f"tool '{tool_name}' not found in source")

            updated_tool = self._parse_tool_file(file) if file else self._load_tool_from_url(url)
            tools[idx] = updated_tool

            payload = {
                "inline_tools": tools,
                "type": "inline",
            }
            endpoint = self._format_endpoint(Endpoints.SOURCE_GET, source_uuid=source_uuid)
            updated = self._put(endpoint=endpoint, data=payload).json()
            return updated if isinstance(updated, dict) else {"result": updated}
        except Exception as e:
            raise SourceError(f"Failed to update inline tool: {e}")

    def list(
        self,
        source_uuid: str,
    ) -> Union[List[Dict[str, Any]], str]:
        """List tools in an inline source."""
        try:
            source = self._get(self._format_endpoint(Endpoints.SOURCE_METADATA, source_uuid=source_uuid)).json()
            tools = source.get("inline_tools", []) if isinstance(source, dict) else []
            return tools
        except Exception as e:
            raise SourceError(f"Failed to list inline tools: {e}")

    def _parse_tool_file(self, file_path: str) -> Dict[str, Any]:
        with open(file_path, "rb") as f:
            content = f.read()
        # YAML preferred when extension matches; otherwise try YAML then JSON
        text = content.decode("utf-8")
        if file_path.endswith((".yaml", ".yml")):
            import yaml  # type: ignore
            return yaml.safe_load(text)
        try:
            import yaml  # type: ignore
            return yaml.safe_load(text)
        except Exception:
            return json.loads(text)

    def _load_tool_from_url(self, tool_url: str) -> Dict[str, Any]:
        import requests

        resp = requests.get(tool_url)
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "")
        text = resp.text
        if "yaml" in content_type or tool_url.endswith((".yaml", ".yml")):
            import yaml
            return yaml.safe_load(text)
        try:
            return resp.json()
        except Exception:
            # Try YAML as fallback
            try:
                import yaml  # type: ignore
                return yaml.safe_load(text)
            except Exception as e:
                raise SourceValidationError(f"failed to parse tool definition: {e}")


class SourceService(BaseService):
    """Service for managing sources"""
    inline = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.inline = _InlineService(self.client)

    def list(
        self,
        full: bool = False,
        debug: bool = False,
        fetch_metadata: bool = False,
        max_concurrent: int = 10
    ) -> List[Dict[str, Any]]:
        """
        List all sources with optional metadata fetching

        Args:
            full: Fetch full metadata for each source
            debug: Enable debug output
            fetch_metadata: Whether to fetch metadata for sources
            max_concurrent: Maximum concurrent metadata requests

        Returns:
            List of source objects
        """
        endpoint = self._format_endpoint(Endpoints.SOURCES_LIST)

        response = self._get(endpoint=endpoint).json()

        if hasattr(response, 'json'):
            try:
                sources = response.json()
            except:
                raise SourceError("Failed to parse sources response")
        else:
            sources = response

        # Set default type if not available
        for source in sources:
            if not source.get('type'):
                if not source.get('url') or source.get('inline_tools') or (source.get('url', '').endswith('.zip')):
                    source['type'] = 'inline'
                else:
                    source['type'] = 'git'

        # Fetch metadata if requested
        if full or fetch_metadata:
            self.__fetch_metadata_concurrent(sources, max_concurrent, debug)

        return sources

    def __get_metadata(
        self,
        uuid: str
    ) -> Dict[str, Any]:
        """
        Get metadata for a specific source

        Args:
            uuid: Source UUID

        Returns:
            Source metadata
        """
        endpoint = self._format_endpoint(Endpoints.SOURCE_METADATA, source_uuid=uuid)

        response = self._get(endpoint=endpoint)

        if hasattr(response, 'json'):
            try:
                return response.json()
            except:
                raise SourceError("Failed to parse source metadata")
        else:
            return response

    def __fetch_metadata_concurrent(self, sources: List[Dict[str, Any]], max_concurrent: int, debug: bool = False):
        """
        Fetch metadata for sources concurrently using ThreadPoolExecutor

        Args:
            sources: List of source objects to fetch metadata for
            max_concurrent: Maximum number of concurrent requests
            debug: Enable debug output
        """
        if not sources:
            return

        # Adjust concurrency based on source count
        if max_concurrent <= 0:
            max_concurrent = 10  # Default
        if max_concurrent > len(sources):
            max_concurrent = len(sources)

        # Progress tracking
        progress = {
            'completed': 0,
            'successful': 0,
            'failed': 0,
            'error_sources': [],
            'lock': threading.Lock()
        }

        def fetch_metadata(index: int):
            """Fetch metadata for a single source"""
            try:
                if debug:
                    logger.info(f"Fetching metadata for {sources[index].get('name')} (UUID: {sources[index].get('uuid')})")

                metadata = self.__get_metadata(sources[index]['uuid'])

                with progress['lock']:
                    progress['completed'] += 1
                    progress['successful'] += 1
                    sources[index].update(metadata)

                    if debug:
                        logger.info(f"Metadata received: Type={metadata.get('type')}, Tools={len(metadata.get('tools', []))}")

            except Exception as e:
                with progress['lock']:
                    progress['completed'] += 1
                    progress['failed'] += 1
                    progress['error_sources'].append(sources[index].get('name', 'Unknown'))

                    if debug:
                        logger.error(f"Failed to get metadata for {sources[index].get('name')}: {e}")

        # Execute concurrent metadata fetching
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            futures = [executor.submit(fetch_metadata, i) for i in range(len(sources))]
            concurrent.futures.wait(futures)

        # Log summary
        if progress['failed'] > 0:
            logger.warning(f"Failed to fetch metadata for {progress['failed']} sources")
            if progress['failed'] <= 3:
                for name in progress['error_sources']:
                    logger.warning(f"  - {name}")

    def scan(
        self,
        source_url: str,
        output_format: str = "table",
        dynamic_config: Optional[Dict[str, Any]] = None,
        runner: Optional[str] = None,
        local: bool = False,
        local_only: bool = False
    ) -> Dict[str, Any]:
        """
        Scan a source URL or local directory for available tools

        Args:
            source_url: URL or path to scan for tools
            output_format: Output format (table|json)
            dynamic_config: Dynamic configuration for the source
            runner: Runner name to use for scanning
            local: Whether this is a local directory scan
            local_only: Force local-only scanning (bypass Git)

        Returns:
            Dictionary containing discovered tools and source information
        """
        try:
            # Handle local directory scanning logic
            if source_url in [".", "./"] or source_url.startswith("/"):
                local = True

            # For local-only scanning, convert to absolute path
            if local and local_only:
                abs_path = os.path.abspath(source_url)
                source_url = abs_path

            # Call the discover method to scan the source
            discovery_result = self.__discover(
                source_url=source_url,
                dynamic_config=dynamic_config,
                runner=runner,
                inline_tools=None
            )

            # Format the output based on the requested format
            if output_format == "json":
                return discovery_result
            else:
                # For table format, return structured data that can be displayed
                return {
                    "source": discovery_result.get("source", {}),
                    "tools": discovery_result.get("tools", []),
                    "errors": discovery_result.get("errors", []),
                    "name": discovery_result.get("name", ""),
                    "scan_successful": len(discovery_result.get("tools", [])) > 0,
                    "source_url": source_url,
                    "runner": runner
                }

        except Exception as e:
            error = SourceError(f"Failed to scan source {source_url}: {str(e)}")
            capture_exception(error)
            raise error

    def __discover(
        self,
        source_url: str = "",
        dynamic_config: Optional[Dict[str, Any]] = None,
        runner: Optional[str] = None,
        inline_tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Discover tools in a source using the discovery API

        Args:
            source_url: Source URL to discover (can be empty for inline tools)
            dynamic_config: Dynamic configuration for discovery
            runner: Runner name to use
            inline_tools: List of inline tools to validate

        Returns:
            Discovery response with tools and source information
        """
        try:
            # Prepare request body
            request_body = {}

            if dynamic_config:
                request_body["dynamic_config"] = dynamic_config

            if inline_tools:
                request_body["inline_tools"] = inline_tools

            # Build endpoint with query parameters
            endpoint = Endpoints.SOURCE_LOAD
            query_params = []

            if source_url:
                query_params.append(f"url={urllib.parse.quote(source_url)}")

            if runner:
                query_params.append(f"runner={runner}")

            if query_params:
                endpoint += "?" + "&".join(query_params)

            # Make the POST request
            response = self._post(endpoint=endpoint, data=request_body, stream=False)

            # Parse the response
            if hasattr(response, 'json'):
                discovery_result = response.json()
            else:
                discovery_result = response

            # Check for errors in the discovery response
            if discovery_result.get("errors"):
                # Return the discovery result with errors for handling by caller
                return discovery_result

            return discovery_result

        except Exception as e:
            error = SourceError(f"Failed to discover source {source_url}: {str(e)}")
            capture_exception(error)
            raise error

    def __create(
        self,
        source_url: str = "",
        name: Optional[str] = None,
        runner: Optional[str] = None,
        dynamic_config: Optional[Dict[str, Any]] = None,
        inline_tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Create a new source

        Args:
            source_url: Source URL (can be empty for inline sources)
            name: Source name
            runner: Runner name
            dynamic_config: Dynamic configuration
            inline_tools: Inline tools for inline sources

        Returns:
            Created source information
        """
        try:
            # First discover/validate the source
            discovery_result = self.__discover(
                source_url=source_url,
                dynamic_config=dynamic_config,
                runner=runner,
                inline_tools=inline_tools
            )

            # Check if discovery had errors
            if discovery_result.get("errors"):
                error_msg = "Source discovery found errors:\n"
                for error in discovery_result["errors"]:
                    error_msg += f"- {error.get('type', 'Error')} in {error.get('file', 'unknown')}: {error.get('error', 'Unknown error')}\n"
                raise SourceError(error_msg)

            # Prepare creation request
            request_body = {
                "url": source_url,
                "tools": discovery_result.get("tools", [])
            }

            if name:
                request_body["name"] = name
            if runner:
                request_body["runner"] = runner
            if dynamic_config:
                request_body["dynamic_config"] = dynamic_config
            if inline_tools:
                request_body["inline_tools"] = inline_tools

            # Create the source
            endpoint = Endpoints.SOURCES_LIST  # POST to /sources creates a new source
            response = self._post(endpoint=endpoint, data=request_body, stream=False)

            if hasattr(response, 'json'):
                return response.json()
            else:
                return response

        except Exception as e:
            if isinstance(e, SourceError):
                raise
            error = SourceError(f"Failed to create source: {str(e)}")
            capture_exception(error)
            raise error

    def __load(self, url: str, name: Optional[str] = None, runner: Optional[str] = None) -> Dict[str, Any]:
        """
        Load a source from URL

        Args:
            url: Source URL to load
            name: Optional name for the source
            runner: Optional runner name

        Returns:
            Loaded source information
        """
        try:
            endpoint = Endpoints.SOURCE_LOAD

            request_body = {
                'url': url
            }

            if name:
                request_body['name'] = name
            if runner:
                request_body['runner'] = runner

            response = self._post(endpoint=endpoint, data=request_body, stream=False)

            if hasattr(response, 'json'):
                return response.json()
            else:
                return response

        except Exception as e:
            error = SourceError(f"Failed to load source from {url}: {str(e)}")
            capture_exception(error)
            raise error

    def add(
        self,
        source_url: str = "",
        name: Optional[str] = None,
        dynamic_config_file: Optional[str] = None,
        inline_file: Optional[str] = None,
        inline_tools: Optional[List[Dict[str, Any]]] = None,
        runner: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add a new source

        Args:
            source_url: Source URL (empty for inline sources)
            name: Source name
            dynamic_config_file: Path to JSON configuration file
            inline_file: Path to file containing inline tool definitions (YAML or JSON)
            inline_tools: List of inline tools (alternative to inline_file)
            runner: Runner name for the source

        Returns:
            Created source information
        """
        try:
            # Check if we're adding an inline source
            if inline_file or inline_tools:
                return self._add_inline_source(
                    name=name,
                    dynamic_config_file=dynamic_config_file,
                    inline_file=inline_file,
                    inline_tools=inline_tools,
                    runner=runner
                )

            # Regular URL-based source
            if not source_url:
                raise SourceError("URL argument is required for non-inline sources")

            # Load dynamic configuration if provided
            dynamic_config = None
            if dynamic_config_file:
                dynamic_config = self.__load_dynamic_config(dynamic_config_file)

            # Create the source
            created = self.__create(
                source_url=source_url,
                name=name,
                runner=runner,
                dynamic_config=dynamic_config
            )

            logger.info(f"\n✅ Source added successfully!")
            logger.info(f"UUID: {created.get('uuid', 'Unknown')}")
            logger.info(f"Tools: {len(created.get('tools', []))}")

            return created

        except Exception as e:
            if isinstance(e, SourceError):
                raise
            error = SourceError(f"Failed to add source: {str(e)}")
            capture_exception(error)
            raise error

    def describe(
        self,
        uuid: str,
        output: str = "text",
    ) -> Union[Dict[str, Any], str]:
        """Show detailed information about a source (metadata)."""
        try:
            endpoint = self._format_endpoint(Endpoints.SOURCE_METADATA, source_uuid=uuid)
            source = self._get(endpoint).json()
            if output == "json":
                return json.dumps(source, indent=2)
            return source
        except Exception as e:
            raise SourceNotFoundError(str(e))

    def delete(
        self,
        uuid: str,
        runner: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Delete a source by UUID.
        Args:
            uuid: UUID of the source to delete
            runner: Optional runner name to use for deletion
        Returns:
            Dictionary with result status or error message
        Raises:
            SourceError: If deletion fails
        """
        try:
            endpoint = self._format_endpoint(Endpoints.SOURCE_DELETE, source_uuid=uuid)
            if runner:
                endpoint = f"{endpoint}?runner={runner}"
            response = self._delete(endpoint).json()
            return response if isinstance(response, dict) else {"result": response}
        except Exception as e:
            raise SourceError(f"Failed to delete source: {e}")

    def sync(
        self,
        uuid: str,
        mode: str = "interactive",
        branch: str = "",
        force: bool = False,
        auto_commit: bool = False,
        no_diff: bool = False,
        runner: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Sync a source by UUID."""
        try:
            endpoint = self._format_endpoint(Endpoints.SOURCE_SYNC, source_uuid=uuid)
            if runner:
                endpoint = f"{endpoint}?runner={runner}"

            body = {
                "mode": mode,
                "branch": branch,
                "force": force,
                "auto_commit": auto_commit,
                "no_diff": no_diff,
            }
            response = self._post(endpoint=endpoint, data=body, stream=False)
            return response if isinstance(response, dict) else {"result": response}
        except Exception as e:
            raise SourceError(f"Failed to sync source: {e}")

    def update(
        self,
        uuid: str,
        name: str = "",
        config: Optional[str] = None,
        inline: Optional[str] = None,
        inline_stdin: bool = False,
        runner: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update an existing source.

            Updating name, runner, dynamic config and/or inline tools.
        """
        try:
            # Get existing source
            current = self._get(self._format_endpoint(Endpoints.SOURCE_GET, source_uuid=uuid))
            if not isinstance(current, dict):
                raise SourceNotFoundError("failed to get source")

            dynamic_config: Optional[Dict[str, Any]] = None
            if config:
                with open(config, "r") as f:
                    dynamic_config = json.load(f)

            updated: Dict[str, Any] = dict(current)

            if inline:
                tools = self.__load_tools_from_file(inline)
                if not tools:
                    raise SourceValidationError("no tools found in the provided source")
                updated["inline_tools"] = tools
                updated["type"] = "inline"
            elif inline_stdin:
                data = sys.stdin.read()
                tools = self.__parse_tools_data(data, "stdin")
                if not tools:
                    raise SourceValidationError("no tools found in stdin")
                updated["inline_tools"] = tools
                updated["type"] = "inline"

            if name:
                updated["name"] = name
            if runner:
                updated["runner"] = runner
            if dynamic_config is not None:
                updated["dynamic_config"] = dynamic_config

            endpoint = self._format_endpoint(Endpoints.SOURCE_GET, source_uuid=uuid)
            response = self._put(endpoint=endpoint, data=updated)
            return response if isinstance(response, dict) else {"result": response}
        except Exception as e:
            raise SourceError(f"Failed to update source: {e}")

    def debug(
        self,
        uuid: str,
        full: bool = False,
        output: str = "text",
        raw: bool = False,
    ) -> Union[Dict[str, Any], str]:
        """
        Debug source metadata with comprehensive information display

        Args:
            uuid: Source UUID to debug
            full: Enable full debugging with detailed information
            output: Output format (text|json)
            raw: Show raw API response

        Returns:
            Debug information in requested format
        """
        try:
            # Get basic source info
            basic_endpoint = self._format_endpoint(Endpoints.SOURCE_GET, source_uuid=uuid)
            basic_response = self._get(basic_endpoint)
            basic_source = basic_response.json() if hasattr(basic_response, 'json') else basic_response

            # Get detailed metadata
            metadata = None
            metadata_error = None
            metadata_endpoint = self._format_endpoint(Endpoints.SOURCE_METADATA, source_uuid=uuid)

            try:
                metadata_response = self._get(metadata_endpoint)
                metadata = metadata_response.json() if hasattr(metadata_response, 'json') else metadata_response
            except Exception as e:
                metadata_error = str(e)

            # Get raw metadata if requested
            raw_metadata = None
            if raw:
                try:
                    raw_response = self._get(metadata_endpoint)
                    raw_metadata = raw_response.text if hasattr(raw_response, 'text') else str(raw_response)
                except Exception as e:
                    raw_metadata = f"Failed to get raw metadata: {e}"

            # Handle raw output first
            if raw and raw_metadata:
                try:
                    # Try to pretty print JSON
                    parsed = json.loads(raw_metadata)
                    return json.dumps(parsed, indent=2)
                except:
                    return raw_metadata

            # Handle JSON output format
            if output == "json":
                result = {"basic_info": basic_source}
                if metadata:
                    result["detailed_info"] = metadata
                if metadata_error:
                    result["metadata_error"] = metadata_error
                return json.dumps(result, indent=2)

            # Text format output with attractive formatting
            output_lines = []
            output_lines.append("\n🔍 Source Debug Information\n")
            output_lines.append("=" * 50)

            # Basic Information Section
            output_lines.append("\n📋 Basic Source Info")
            output_lines.append("-" * 20)
            output_lines.append(f"UUID: {basic_source.get('uuid', 'N/A')}")
            output_lines.append(f"Name: {basic_source.get('name', 'N/A')}")
            output_lines.append(f"Type: {self._get_source_type(basic_source)}")
            output_lines.append(f"URL: {basic_source.get('url', 'N/A')}")

            if basic_source.get('runner'):
                output_lines.append(f"Runner: {basic_source['runner']}")

            # Show timestamps if available
            if basic_source.get('created_at'):
                try:
                    created_at = datetime.fromisoformat(basic_source['created_at'].replace('Z', '+00:00'))
                    output_lines.append(f"Created: {created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                except:
                    output_lines.append(f"Created: {basic_source['created_at']}")

            if basic_source.get('updated_at'):
                try:
                    updated_at = datetime.fromisoformat(basic_source['updated_at'].replace('Z', '+00:00'))
                    output_lines.append(f"Updated: {updated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                except:
                    output_lines.append(f"Updated: {basic_source['updated_at']}")

            # Stats section
            output_lines.append("\n📊 Stats")
            output_lines.append("-" * 10)

            regular_tools = len(basic_source.get('tools', []))
            inline_tools = len(basic_source.get('inline_tools', []))
            total_tools = regular_tools + inline_tools
            output_lines.append(f"Tools count: {total_tools} ({regular_tools} regular, {inline_tools} inline)")

            # Connection stats if available
            if basic_source.get('connected_agents_count', 0) > 0:
                output_lines.append(f"Connected Agents: {basic_source['connected_agents_count']}")
            if basic_source.get('connected_tools_count', 0) > 0:
                output_lines.append(f"Connected Tools: {basic_source['connected_tools_count']}")
            if basic_source.get('connected_workflows_count', 0) > 0:
                output_lines.append(f"Connected Workflows: {basic_source['connected_workflows_count']}")
            if basic_source.get('errors_count', 0) > 0:
                output_lines.append(f"⚠️ Errors: {basic_source['errors_count']}")

            # Handle metadata fetch failure
            if metadata_error:
                output_lines.append(f"\n❌ Failed to fetch detailed metadata")
                output_lines.append(f"Error: {metadata_error}")

                output_lines.append("\n🛠️ Troubleshooting Options")
                output_lines.append("• Verify API key and permissions")
                output_lines.append("• Check network connectivity")
                output_lines.append("• Try with raw=True to see raw API response")
                output_lines.append(f"• Try syncing the source: source_service.sync('{uuid}')")

                # Show sample of raw response if available and not already in raw mode
                if raw_metadata and not raw:
                    output_lines.append("\n🔍 Raw Metadata Sample (first 500 chars)")
                    sample = raw_metadata[:500] + "..." if len(raw_metadata) > 500 else raw_metadata
                    output_lines.append(sample)

                return "\n".join(output_lines)

            # Detailed tool information
            if metadata and (metadata.get('tools') or metadata.get('inline_tools')):
                output_lines.append("\n🛠️ Tools")
                output_lines.append("-" * 10)

                # Regular tools
                if metadata.get('tools'):
                    tools = metadata['tools']
                    output_lines.append(f"\nRegular Tools ({len(tools)})")
                    for i, tool in enumerate(tools, 1):
                        tool_type_emoji = self._get_tool_emoji(tool.get('type', ''))
                        output_lines.append(f"{i}. {tool_type_emoji} {tool.get('name', 'Unknown')}")

                        if tool.get('description'):
                            output_lines.append(f"   {tool['description']}")

                        if full:
                            # Detailed information in full debug mode
                            output_lines.append(f"   - Type: {tool.get('type', 'N/A')}")
                            if tool.get('with_files'):
                                output_lines.append(f"   - WithFiles: {tool['with_files']}")
                            if tool.get('with_volumes'):
                                output_lines.append(f"   - WithVolumes: {tool['with_volumes']}")
                            if tool.get('metadata'):
                                output_lines.append("   - Has Metadata: yes")
                            output_lines.append(f"   - Args: {len(tool.get('args', []))}")
                            if tool.get('long_running'):
                                output_lines.append("   - Long Running: ⚠️ yes")
                        else:
                            # Simplified view
                            args = tool.get('args', [])
                            required_args = sum(1 for arg in args if isinstance(arg, dict) and arg.get('required', False))
                            output_lines.append(f"   - Args: {len(args)} ({required_args} required)")

                        output_lines.append("")

                # Inline tools
                if metadata.get('inline_tools'):
                    inline_tools_list = metadata['inline_tools']
                    output_lines.append(f"\nInline Tools ({len(inline_tools_list)})")
                    for i, tool in enumerate(inline_tools_list, 1):
                        output_lines.append(f"{i}. 📝 {tool.get('name', 'Unknown')}")

                        if tool.get('description'):
                            output_lines.append(f"   {tool['description']}")

                        if full:
                            # Detailed information in full debug mode
                            output_lines.append(f"   - Type: {tool.get('type', 'N/A')}")
                            if tool.get('with_files'):
                                output_lines.append(f"   - WithFiles: {tool['with_files']}")
                            if tool.get('with_volumes'):
                                output_lines.append(f"   - WithVolumes: {tool['with_volumes']}")
                            if tool.get('metadata'):
                                output_lines.append("   - Has Metadata: yes")
                            output_lines.append(f"   - Args: {len(tool.get('args', []))}")
                            if tool.get('long_running'):
                                output_lines.append("   - Long Running: ⚠️ yes")
                        else:
                            # Simplified view
                            args = tool.get('args', [])
                            required_args = sum(1 for arg in args if isinstance(arg, dict) and arg.get('required', False))
                            output_lines.append(f"   - Args: {len(args)} ({required_args} required)")

                        output_lines.append("")

            # Dynamic configuration section
            if metadata and metadata.get('dynamic_config'):
                output_lines.append("\n⚙️ Dynamic Configuration")
                output_lines.append("-" * 25)
                try:
                    config_json = json.dumps(metadata['dynamic_config'], indent=2)
                    output_lines.append(config_json)
                except:
                    output_lines.append(str(metadata['dynamic_config']))

            # Helpful operations section (adapted for SDK usage)
            output_lines.append("\n📚 Helpful Operations")
            output_lines.append("-" * 20)
            output_lines.append(f"• Get tools: tools.list(source_uuid='{uuid}')")
            output_lines.append(f"• Sync source: sources.sync('{uuid}')")
            output_lines.append(f"• Update source: sources.update('{uuid}', name='New Name')")
            output_lines.append(f"• Delete source: sources.delete('{uuid}')")

            return "\n".join(output_lines)

        except Exception as e:
            raise SourceError(f"Failed to debug source: {e}")

    def _get_source_type(self, source: Dict[str, Any]) -> str:
        """Determine the source type based on source data"""
        if source.get('type'):
            return source['type']

        if not source.get('url') or source.get('inline_tools') or (source.get('url', '').endswith('.zip')):
            return 'inline'
        else:
            return 'git'

    def _get_tool_emoji(self, tool_type: str) -> str:
        """Get emoji for tool type"""
        emoji_map = {
            'function': '🔧',
            'workflow': '⚙️',
            'script': '📜',
            'command': '💻',
        }
        return emoji_map.get(tool_type, '🧰')

    def _add_inline_source(
        self,
        name: Optional[str] = None,
        dynamic_config_file: Optional[str] = None,
        inline_file: Optional[str] = None,
        inline_tools: Optional[List[Dict[str, Any]]] = None,
        runner: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add an inline source with tools
        """
        try:
            # Get tools from file or provided list
            tools = []
            if inline_file:
                tools = self.__load_tools_from_file(inline_file)
            elif inline_tools:
                tools = inline_tools
            else:
                raise SourceError("Must provide either inline_file or inline_tools")

            if not tools:
                raise SourceError("No tools found in the provided source")

            tools_count = len(tools)

            # Load dynamic configuration if provided
            dynamic_config = None
            if dynamic_config_file:
                dynamic_config = self.__load_dynamic_config(dynamic_config_file)

            # Create the inline source
            created = self.__create(
                source_url="",  # Empty for inline sources
                name=name,
                runner=runner,
                dynamic_config=dynamic_config,
                inline_tools=tools
            )

            logger.info(f"\n✅ Inline source added successfully!")
            logger.info(f"UUID: {created.get('uuid', 'Unknown')}")
            logger.info(f"Tools: {tools_count}")

            return created

        except Exception as e:
            if isinstance(e, SourceError):
                raise
            error = SourceError(f"Failed to add inline source: {str(e)}")
            capture_exception(error)
            raise error

    def __load_tools_from_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Load tools from a YAML or JSON file
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = f.read()

            return self.__parse_tools_data(data, file_path)

        except Exception as e:
            raise SourceError(f"Failed to load tools from file {file_path}: {str(e)}")

    def __parse_tools_data(self, data: str, filename: str = "") -> List[Dict[str, Any]]:
        """
        Parse tools data from YAML or JSON string
        """
        try:
            # Determine format based on file extension or content
            is_json = False
            if filename:
                if filename.lower().endswith('.json'):
                    is_json = True
            else:
                # Try to determine from content
                trimmed = data.strip()
                if trimmed and (trimmed[0] == '{' or trimmed[0] == '['):
                    is_json = True

            if is_json:
                try:
                    tools = json.loads(data)
                    # If it's a single tool, wrap in a list
                    if isinstance(tools, dict):
                        tools = [tools]
                    return tools
                except json.JSONDecodeError as e:
                    raise SourceError(f"Failed to parse JSON: {str(e)}")
            else:
                # Parse as YAML
                try:
                    import yaml
                    tools = yaml.safe_load(data)
                    # If it's a single tool, wrap in a list
                    if isinstance(tools, dict):
                        tools = [tools]
                    return tools if tools else []
                except Exception as e:
                    raise SourceError(f"Failed to parse YAML: {str(e)}")

        except Exception as e:
            if isinstance(e, SourceError):
                raise
            raise SourceError(f"Failed to parse tools data: {str(e)}")

    def __load_dynamic_config(self, config_file: str) -> Dict[str, Any]:
        """
        Load dynamic configuration from a JSON file
        """
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = f.read()

            config = json.loads(data)
            return config

        except Exception as e:
            raise SourceError(f"Failed to load dynamic config from {config_file}: {str(e)}")
