"""
Documentation service for querying the central knowledge base using Trieve
"""
import json
import logging
import requests
from typing import Dict, Any, List

from kubiya_workflow_sdk import capture_exception
from kubiya_workflow_sdk.kubiya_services.exceptions import DocumentationError
from kubiya_workflow_sdk.kubiya_services.services.base import BaseService

logger = logging.getLogger(__name__)


class DocumentationService(BaseService):
    """
    Service for querying documentation using Trieve API

    This service provides access to the central knowledge base for documentation queries.
    """

    KUBIYA_BASE_TRIEVE_URL = "https://leaves.mintlify.com/api/mcp/config/kubiya"
    GROUP_SEARCH_URL = "https://api.mintlifytrieve.com/api/chunk_group/group_oriented_search"

    _trieve_config = None

    def query(
        self,
        prompt: str,
        page_size: int = 10,
        search_type: str = "bm25",
        extend_results: bool = True,
        score_threshold: float = 1.0,
        render_markdown: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Query the documentation knowledge base using Trieve API

        Args:
            prompt: The search query/prompt to look for in documentation
            page_size: Number of results to return (default: 10)
            search_type: Type of search to perform (default: "bm25")
            extend_results: Whether to extend results with additional context (default: True)
            score_threshold: Minimum score threshold for results (default: 1.0)
            render_markdown: Whether to format output as markdown (default: True)

        Returns:
            List of search results with formatted content

        Raises:
            DocumentationError: If the query fails or configuration cannot be retrieved
        """
        try:
            # Get Trieve configuration
            trieve_config = self._get_trieve_config()

            # Prepare search request
            search_request = {
                "query": prompt,
                "page_size": page_size,
                "search_type": search_type,
                "extend_results": extend_results,
                "score_threshold": score_threshold
            }

            # Make request to Trieve API
            response = self._search_documentation_by_group(trieve_config, search_request)

            # Format results
            formatted_results = self._format_search_results(response, render_markdown)

            return formatted_results

        except Exception as e:
            error = DocumentationError(f"Documentation query failed: {str(e)}")
            capture_exception(error)
            raise error

    def _get_trieve_config(self) -> Dict[str, Any]:
        """
        Get Trieve configuration from the API

        Returns:
            Dictionary containing Trieve API configuration

        Raises:
            DocumentationError: If configuration cannot be retrieved
        """
        if self._trieve_config is not None:
            return self._trieve_config

        try:
            response = requests.get(self.KUBIYA_BASE_TRIEVE_URL, timeout=30)
            response.raise_for_status()

            config = response.json()

            # Validate required fields
            required_fields = ['trieveApiKey', 'trieveDatasetId', 'name']
            for field in required_fields:
                if field not in config:
                    raise DocumentationError(f"Missing required field in Trieve config: {field}")

            self._trieve_config = {
                'api_key': config['trieveApiKey'],
                'dataset_id': config['trieveDatasetId'],
                'organization': config['name']
            }

            return self._trieve_config

        except requests.RequestException as e:
            raise DocumentationError(f"Failed to fetch Trieve config: {str(e)}")
        except (KeyError, json.JSONDecodeError) as e:
            raise DocumentationError(f"Invalid Trieve config response: {str(e)}")

    def _search_documentation_by_group(
        self,
        trieve_config: Dict[str, Any],
        search_request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Search documentation using Trieve group-oriented search

        Args:
            trieve_config: Trieve API configuration
            search_request: Search request parameters

        Returns:
            Search response from Trieve API

        Raises:
            DocumentationError: If search request fails
        """
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f"Bearer {trieve_config['api_key']}",
            'TR-Dataset': trieve_config['dataset_id'],
            'TR-Organization': trieve_config['organization'],
            'X-API-VERSION': 'V2'
        }

        try:
            response = requests.post(
                self.GROUP_SEARCH_URL,
                headers=headers,
                json=search_request,
                timeout=60
            )
            response.raise_for_status()

            result = response.json()

            # Validate response structure
            if 'results' not in result:
                raise DocumentationError("Invalid search response: missing 'results' field")

            if not result['results']:
                raise DocumentationError(f"No results found for query: {search_request['query']}")

            return result

        except requests.RequestException as e:
            raise DocumentationError(f"Failed to search documentation: {str(e)}")
        except json.JSONDecodeError as e:
            raise DocumentationError(f"Invalid JSON response from Trieve: {str(e)}")

    def _format_search_results(
        self,
        search_response: Dict[str, Any],
        render_markdown: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Format search results for display

        Args:
            search_response: Raw search response from Trieve
            render_markdown: Whether to format content as markdown

        Returns:
            List of formatted search results
        """
        formatted_results = []

        for group in search_response.get('results', []):
            group_name = group.get('group', {}).get('name', 'Unknown Group')

            for chunk_data in group.get('chunks', []):
                chunk = chunk_data.get('chunk', {})

                # Extract chunk data
                title = chunk.get('metadata', {}).get('title', 'Untitled')
                icon = chunk.get('metadata', {}).get('icon', '📄')
                html_content = chunk.get('chunk_html', '')
                tag_sets = chunk.get('tag_set', [])

                # Determine if this is code content
                is_code = 'code' in tag_sets

                # Format content
                if render_markdown:
                    if is_code:
                        formatted_content = f"```\n{html_content}\n```"
                    else:
                        # Replace single newlines with double newlines for proper markdown formatting
                        formatted_content = html_content.replace('\n', '\n\n')

                    # Format title
                    formatted_title = f"# {icon} {title}"
                else:
                    formatted_content = html_content
                    formatted_title = f"{icon} {title}"

                formatted_result = {
                    'group': group_name,
                    'title': title,
                    'formatted_title': formatted_title,
                    'icon': icon,
                    'content': formatted_content,
                    'raw_content': html_content,
                    'is_code': is_code,
                    'tags': tag_sets,
                    'metadata': chunk.get('metadata', {})
                }

                formatted_results.append(formatted_result)

        return formatted_results
