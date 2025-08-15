"""
Tool service for managing tools
"""
import json
import logging
import os
import shutil
import uuid
from typing import Optional, Dict, Any, List, Union

from kubiya_workflow_sdk import capture_exception
from kubiya_workflow_sdk.kubiya_services.constants import Endpoints
from kubiya_workflow_sdk.kubiya_services.exceptions import ToolExecutionError, ToolNotFoundError, ToolGenerationError
from kubiya_workflow_sdk.kubiya_services.services.base import BaseService

logger = logging.getLogger(__name__)


class ToolService(BaseService):
    """Service for managing tools"""

    def list(
            self,
            source_uuid: Optional[str] = None,
            output_format: str = "dict"
    ) -> Union[List[Dict[str, Any]], str]:
        """
        List tools from all sources or a specific source

        Args:
            source_uuid: Optional source UUID to list tools from specific source
            output_format: Output format ("dict" or "json")

        Returns:
            List of tools or JSON string
        """
        try:
            if source_uuid:
                # Get tools from specific source
                source = self._get_source_metadata(source_uuid)
                tools = source.get("tools", [])
                # Also include inline tools if available
                tools.extend(source.get("inline_tools", []))
            else:
                # Get tools from all sources
                sources = self._list_sources()
                tools = []

                for source in sources:
                    try:
                        metadata = self._get_source_metadata(source["uuid"])
                        tools.extend(metadata.get("tools", []))
                        tools.extend(metadata.get("inline_tools", []))
                    except Exception:
                        # Continue if one source fails
                        continue

            if output_format == "json":
                return json.dumps(tools, indent=2)

            return tools

        except Exception as e:
            error = ToolExecutionError(f"Failed to list tools: {str(e)}")
            capture_exception(error)
            raise error

    def search(
        self,
        query: str,
        non_interactive: bool = False,
        output_format: str = "dict"
    ) -> Union[List[Dict[str, Any]], str]:
        """
        Search for tools by query

        Args:
            query: Search query
            non_interactive: Non-interactive search mode
            output_format: Output format ("dict" or "json")

        Returns:
            List of matching tools with scores or JSON string
        """
        try:
            query_lower = query.lower()
            matches = []

            # Get all sources
            sources = self._list_sources()

            # Pre-filter sources based on name/description prefix match
            relevant_sources = []
            for source in sources:
                source_name = source.get("name", "").lower()
                source_desc = source.get("description", "").lower()

                if (query_lower in source_name or query_lower in source_desc or
                        any(source_name.startswith(word) or source_desc.startswith(word)
                            for word in query_lower.split())):
                    relevant_sources.append(source)

            # If no relevant sources found, search all sources
            if not relevant_sources:
                relevant_sources = sources

            # Search through relevant sources
            for source in relevant_sources:
                try:
                    metadata = self._get_source_metadata(source["uuid"])

                    # Search through tools
                    for tool in metadata.get("tools", []):
                        tool_name = tool.get("name", "").lower()
                        tool_desc = tool.get("description", "").lower()

                        # Prioritize exact matches
                        if query_lower in tool_name or query_lower in tool_desc:
                            distance = 0
                        else:
                            # Calculate Levenshtein distance for close matches
                            name_distance = self._levenshtein_distance(tool_name, query_lower)
                            desc_distance = self._levenshtein_distance(tool_desc, query_lower)
                            distance = min(name_distance, desc_distance)

                        if distance <= len(query_lower) // 2:
                            matches.append({
                                "tool": tool,
                                "source": source,
                                "distance": distance
                            })

                except Exception:
                    continue

            # Sort by distance (lower is better), then by name
            matches.sort(key=lambda x: (x["distance"], x["tool"].get("name", "")))

            # Limit to top 10 matches
            matches = matches[:10]

            if output_format == "json":
                return json.dumps(matches, indent=2)

            return matches

        except Exception as e:
            error = ToolExecutionError(f"Failed to search tools: {str(e)}")
            capture_exception(error)
            raise error

    def describe(
            self,
            tool_name: str,
            source_uuid: Optional[str] = None,
            output_format: str = "dict"
    ) -> Union[Dict[str, Any], str]:
        """
        Show detailed information about a tool

        Args:
            tool_name: Name of the tool to describe
            source_uuid: Optional source UUID to search in specific source
            output_format: Output format ("dict" or "json")

        Returns:
            Tool details or JSON string
        """
        try:
            tool = None
            source_name = None

            if source_uuid:
                # Get tool from specific source
                source = self._get_source_metadata(source_uuid)

                # Check regular tools
                for t in source.get("tools", []):
                    if t.get("name") == tool_name:
                        tool = t
                        source_name = source.get("name")
                        break

                # Check inline tools if not found
                if not tool:
                    for t in source.get("inline_tools", []):
                        if t.get("name") == tool_name:
                            tool = t
                            source_name = source.get("name")
                            break
            else:
                # Search all sources
                sources = self._list_sources()

                for source in sources:
                    try:
                        metadata = self._get_source_metadata(source["uuid"])

                        # Check regular tools
                        for t in metadata.get("tools", []):
                            if t.get("name") == tool_name:
                                tool = t
                                source_name = source.get("name")
                                break

                        if tool:
                            break

                        # Check inline tools
                        for t in metadata.get("inline_tools", []):
                            if t.get("name") == tool_name:
                                tool = t
                                source_name = source.get("name")
                                break

                        if tool:
                            break
                    except Exception:
                        continue

            if not tool:
                raise ToolNotFoundError(f"Tool '{tool_name}' not found")

            result = {
                "tool": tool,
                "source_name": source_name
            }

            if output_format == "json":
                return json.dumps(result, indent=2)

            return result

        except ToolNotFoundError:
            raise
        except Exception as e:
            error = ToolExecutionError(f"Failed to describe tool: {str(e)}")
            capture_exception(error)
            raise error


    # Helper methods
    def _list_sources(self) -> List[Dict[str, Any]]:
        """List all sources"""
        endpoint = self._format_endpoint(Endpoints.SOURCES_LIST)
        response = self._get(endpoint).json()
        return response if isinstance(response, list) else []

    def _get_source_metadata(self, source_uuid: str) -> Dict[str, Any]:
        """Get source metadata"""
        endpoint = self._format_endpoint(Endpoints.SOURCE_METADATA, source_uuid=source_uuid)
        return self._get(endpoint).json()

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings"""
        if len(s1) < len(s2):
            s1, s2 = s2, s1

        if len(s2) == 0:
            return len(s1)

        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def generate_tool(
        self,
        description: str,
        session_id: Optional[str] = None,
        target_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a new tool from description

        Args:
            description: Tool description (required)
            session_id: Session ID for continuing previous generation (auto-generated if not provided)
            target_dir: Target directory for generated files (default: current directory)

        Returns:
            For streaming: Generator yielding event data with file creation info
            For non-streaming: Final response data with file paths

        Raises:
            ToolGenerationError: If tool generation fails
        """
        if not description:
            error = ToolGenerationError("Tool description is required")
            capture_exception(error)
            raise error

        # Generate a session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())

        # If no target directory is given, use the current working directory
        if not target_dir:
            target_dir = os.getcwd()

        # Create session directory
        session_dir = os.path.join(target_dir, session_id)
        try:
            os.makedirs(session_dir, exist_ok=True)
            logger.info(f"📁 Using session directory: {session_dir}")
        except OSError as e:
            error = ToolGenerationError(f"Failed to create session directory: {str(e)}")
            capture_exception(error)
            raise error

        try:
            logger.info(f"🎯 Generating tool from description: {description}")
            logger.info(f"🔑 Using session ID: {session_id}")
            logger.info("🚀 Starting tool generation...")

            request_body = {
                "message": description,
                "session_id": session_id
            }

            endpoint = Endpoints.TOOL_GENERATE

            response = self._post(
                endpoint=endpoint,
                data=request_body,
                stream=True
            )
            events = []
            for event in response:
                events.append(event)

            files_created = self._process_generation_events(
                events, session_dir
            )

            return {
                "events": events,
                "session_id": session_id,
                "session_dir": session_dir,
                "files_created": files_created
            }

        except Exception as e:
            error = ToolGenerationError(f"Failed to generate tool: {str(e)}")
            capture_exception(error)
            if os.path.exists(session_dir) and os.path.isdir(session_dir):
                shutil.rmtree(session_dir)
            raise error

    def _process_generation_events(
        self,
        events: List[Dict[str, Any]],
        session_dir: str,
    ) -> List[str]:
        """
        Process a list of generation events and write files

        Args:
            events: List of event data
            session_dir: Session directory path

        Returns:
            List of file paths that were created
        """
        file_buffers = {}
        files_created = []

        for event in events:
            generated_content = event.get('generated_tool_content', [])
            if not generated_content:
                continue

            if event.get('type') == 'error':
                error_msg = generated_content[0].get('content',
                                                     'Unknown error') if generated_content else 'Unknown error'
                raise ToolGenerationError(f"Generation error: {error_msg}")

            files_written = self._process_file_content(
                generated_content, file_buffers, session_dir
            )
            files_created.extend(files_written)

        if not files_created:
            raise ToolGenerationError("No files were created during tool generation")

        logger.info(f"✨ Tool generation completed successfully in: {session_dir}")
        return files_created

    def _process_file_content(
        self,
        generated_content: List[Dict[str, Any]],
        file_buffers: Dict[str, Dict[str, Any]],
        session_dir: str
    ) -> List[str]:
        """
        Process generated file content and write files to disk

        Args:
            generated_content: List of generated content items
            file_buffers: Dictionary tracking file buffers
            session_dir: Session directory path

        Returns:
            List of file paths that were written
        """
        files_written = []

        for content_item in generated_content:
            file_name = content_item.get('file_name', '')
            content = content_item.get('content', '')

            # Skip if no filename or if filename is incomplete
            if not file_name or '.' not in file_name:
                continue

            # Get or create buffer for this file
            if file_name not in file_buffers:
                file_buffers[file_name] = {
                    'content': '',
                    'file_name': file_name
                }

            # Clean up content by removing any partial message artifacts
            clean_content = content
            if clean_content.startswith("from kubiya_sdk"):
                # This is a complete file content, replace existing buffer
                file_buffers[file_name]['content'] = clean_content
            elif clean_content.startswith(("FileName:", "Content:")):
                # Skip metadata messages
                continue
            else:
                # Append to existing content
                file_buffers[file_name]['content'] += clean_content

        # Write all buffered files that have content
        for file_name, buffer_info in file_buffers.items():
            content = buffer_info['content']

            # Skip empty files
            if not content:
                continue

            # Skip if content is just metadata
            if content.startswith("FileName:"):
                continue

            full_path = os.path.join(session_dir, file_name)
            dir_path = os.path.dirname(full_path)

            logger.info(f"📥 Writing file: {file_name}")

            try:
                # Make sure the directory structure exists
                os.makedirs(dir_path, exist_ok=True)

                # Write the file content to disk
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                logger.info(f"✅ Created file: {file_name} ({len(content)} bytes)")
                files_written.append(full_path)

                # Clear the buffer after writing
                file_buffers[file_name]['content'] = ''

            except IOError as e:
                logger.error(f"Failed to write file {full_path}: {e}")
                continue

        return files_written