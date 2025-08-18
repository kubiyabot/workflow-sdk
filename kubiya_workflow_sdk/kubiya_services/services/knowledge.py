"""
Knowledge service for managing knowledge base queries
"""
import logging
import os
from typing import Optional, Dict, Any, Union, Generator

from kubiya_workflow_sdk.kubiya_services.constants import Endpoints
from kubiya_workflow_sdk.kubiya_services.exceptions import KnowledgeError
from kubiya_workflow_sdk.kubiya_services.services.base import BaseService
from kubiya_workflow_sdk.kubiya_services.utils import to_bool

logger = logging.getLogger(__name__)


class KnowledgeService(BaseService):
    """Service for managing knowledge base queries and operations"""

    def query(
        self,
        prompt: str,
        stream: bool = True,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None
    ) -> Union[Dict[str, Any], Generator[str, None, None]]:
        """
        Query the central knowledge base for contextual information with intelligent search capabilities.

        This provides intelligent search capabilities across all available data sources
        in the central knowledge base, with real-time streaming updates on search progress.

        Features:
        - Semantic search across multiple data sources
        - Real-time progress updates during search (with stream=True)
        - Intelligent result summarization
        - Related query suggestions
        - Source tracking and metadata

        Args:
            prompt: The query string to search for in the knowledge base
            stream: Whether to stream the response in real-time (default: True)
            user_id: User ID for the query (optional)
            org_id: Organization ID for the query (optional)

        Returns:
            For streaming: Generator yielding event data
            For non-streaming: Final response data

        Raises:
            KnowledgeError: If the query fails
        """
        # Get orchestrator URL from environment or use default
        orchestrator_url = os.getenv("KUBIYA_ORCHESTRATOR_URL")
        if not orchestrator_url:
            # Check if we should use the same base URL as the main API
            if to_bool(os.getenv("KUBIYA_USE_SAME_API")):
                # Use the client's base URL with orchestrator endpoint
                orchestrator_url = self.client.base_url
            else:
                # Default to the orchestrator service URL
                orchestrator_url = "https://orchestrator.kubiya.ai"

        # Prepare request body
        request_body = {
            "query": prompt
        }

        endpoint = Endpoints.KNOWLEDGE_QUERY

        # Add optional parameters if provided
        if user_id: request_body["userID"] = user_id
        if org_id: request_body["orgID"] = org_id

        # Make the POST request - use orchestrator URL directly
        # Note: The actual HTTP client implementation would handle auth headers
        try:
            return self._post(
                endpoint=endpoint,
                data=request_body,
                stream=stream,
                base_url=orchestrator_url
            ).json()
        except Exception as e:
            if "timeout" in str(e).lower() or "deadline exceeded" in str(e).lower():
                raise KnowledgeError(
                    "Knowledge base query timeout. The service might be unavailable or slow. Please try again later")
            raise KnowledgeError(f"Failed to query knowledge base: {str(e)}")
