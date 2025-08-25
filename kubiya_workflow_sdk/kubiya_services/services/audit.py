"""
Audit service for managing audit logs and monitoring
"""
import json
import logging
from typing import Optional, Dict, Any, Union, Generator, List
from datetime import datetime, timedelta, UTC

from kubiya_workflow_sdk import capture_exception
from kubiya_workflow_sdk.kubiya_services.constants import Endpoints
from kubiya_workflow_sdk.kubiya_services.exceptions import AuditError
from kubiya_workflow_sdk.kubiya_services.services.base import BaseService

logger = logging.getLogger(__name__)


class AuditService(BaseService):
    """Service for managing audit logs and monitoring"""

    def list(
        self,
        category_type: Optional[str] = None,
        category_name: Optional[str] = None,
        resource_type: Optional[str] = None,
        action_type: Optional[str] = None,
        session_id: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
        sort_direction: str = "desc",
        limit: Optional[int] = None,
    ) -> Union[Dict[str, Any], str]:
        """
        List audit logs with filtering and pagination support.

        Args:
            category_type: Filter by category type (e.g., 'agents', 'workflows')
            category_name: Filter by category name
            resource_type: Filter by resource type
            action_type: Filter by action type
            session_id: Filter by session ID
            start_time: Start time in RFC3339 format (e.g., '2023-04-01T00:00:00Z')
            end_time: End time in RFC3339 format (e.g., '2023-04-02T00:00:00Z')
            page: Page number for pagination (default: 1)
            page_size: Number of items per page (default: 50)
            sort_direction: Sort direction ('asc' or 'desc', default: 'desc')
            limit: Maximum number of items to return

        Returns:
            Dictionary containing:
            - items: List of audit log entries
            - pagination: Pagination information
            - success: Boolean indicating success

        Raises:
            AuditError: If the audit query fails
        """
        try:
            # Set default time range if not provided (last 24 hours)
            if not start_time:
                start_time = (datetime.now(UTC) - timedelta(hours=24)).strftime('%Y-%m-%dT%H:%M:%SZ')

            # Validate time formats if provided
            if start_time:
                self._validate_time_format(start_time)
            if end_time:
                self._validate_time_format(end_time)

            # Build query parameters
            query = self._build_audit_query(
                category_type=category_type,
                category_name=category_name,
                resource_type=resource_type,
                action_type=action_type,
                session_id=session_id,
                start_time=start_time,
                end_time=end_time,
                page=page,
                page_size=page_size,
                sort_direction=sort_direction
            )

            # Make the request - audit uses GET with query parameters
            endpoint = self._build_audit_endpoint(Endpoints.AUDIT_LIST, query)
            response = self._get(endpoint=endpoint)

            # Handle response
            if hasattr(response, 'json'):
                try:
                    result = response.json()
                except:
                    error = AuditError("Failed to parse audit response")
                    capture_exception(error)
                    raise error
            else:
                result = response

            # Apply limit if specified
            if limit and isinstance(result, dict) and 'items' in result:
                if len(result['items']) > limit:
                    result['items'] = result['items'][:limit]
            elif limit and isinstance(result, list):
                if len(result) > limit:
                    result = result[:limit]

            # Format output
            return result

        except Exception as e:
            error = AuditError(f"Failed to list audit logs: {str(e)}")
            capture_exception(error)
            raise error

    def stream(
        self,
        category_type: Optional[str] = None,
        category_name: Optional[str] = None,
        resource_type: Optional[str] = None,
        action_type: Optional[str] = None,
        session_id: Optional[str] = None,
        start_time: Optional[str] = None,
        timeout_minutes: Optional[int] = None,
        verbose: bool = True,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Stream audit logs in real-time using polling.

        Args:
            category_type: Filter by category type
            category_name: Filter by category name
            resource_type: Filter by resource type
            action_type: Filter by action type
            session_id: Filter by session ID
            start_time: Start time in RFC3339 format (default: 5 minutes ago)
            timeout_minutes: Auto-stop streaming after specified minutes
            verbose: Include verbose logging information

        Yields:
            Dict[str, Any]: Individual audit log entries as they arrive

        Raises:
            AuditError: If the audit stream fails to start
        """
        import time

        try:
            # Set default start time if not provided (5 minutes ago)
            if not start_time:
                start_time = (datetime.now(UTC) - timedelta(minutes=5)).strftime('%Y-%m-%dT%H:%M:%SZ')

            # Validate time format
            if start_time:
                self._validate_time_format(start_time)

            # Track processed events to avoid duplicates
            processed_events = set()
            latest_timestamp = start_time
            poll_count = 0
            poll_interval = 3
            start_poll_time = datetime.now(UTC)

            # Calculate end time if timeout is specified
            end_time = None
            if timeout_minutes:
                end_time = datetime.now(UTC) + timedelta(minutes=timeout_minutes)

            if verbose:
                logger.info(f"Initial timestamp filter: {start_time}")

            while True:
                # Check timeout
                if end_time and datetime.now(UTC) >= end_time:
                    if verbose:
                        logger.info(f"Streaming stopped after timeout ({timeout_minutes} minutes)")
                    break

                poll_count += 1

                # Build query parameters for current poll
                query = self._build_audit_query(
                    category_type=category_type,
                    category_name=category_name,
                    resource_type=resource_type,
                    action_type=action_type,
                    session_id=session_id,
                    start_time=latest_timestamp,
                    page=1,
                    page_size=50,
                    sort_direction="desc"
                )

                if verbose or poll_count % 10 == 0:
                    logger.info(f"Poll attempt #{poll_count} - timestamp filter: {latest_timestamp}")

                try:
                    # Poll for new audit items using regular list endpoint
                    endpoint = self._build_audit_endpoint(Endpoints.AUDIT_LIST, query)
                    response = self._get(endpoint=endpoint)

                    # Parse response
                    if hasattr(response, 'json'):
                        try:
                            result = response.json()
                        except:
                            if verbose:
                                logger.error("Failed to parse audit response during streaming")
                            time.sleep(poll_interval)
                            continue
                    else:
                        result = response

                    # Extract items
                    if isinstance(result, dict) and 'items' in result:
                        audit_items = result['items']
                    elif isinstance(result, list):
                        audit_items = result
                    else:
                        audit_items = []

                    if verbose and len(audit_items) > 0:
                        logger.info(f"Found {len(audit_items)} events in poll #{poll_count}")

                    # Process items if any found
                    if audit_items:
                        for item in audit_items:
                            # Create event key to avoid duplicates
                            event_key = f"{item.get('timestamp', '')}-{item.get('category_type', '')}-{item.get('category_name', '')}-{item.get('action_type', '')}"

                            # Skip if we've already processed this event
                            if event_key in processed_events:
                                continue

                            # Mark this event as processed
                            processed_events.add(event_key)

                            # Update latest timestamp if newer
                            item_timestamp = item.get('timestamp', '')
                            if item_timestamp > latest_timestamp:
                                latest_timestamp = item_timestamp
                                if verbose:
                                    logger.info(f"Updated timestamp filter to: {latest_timestamp}")

                            # Yield the audit event
                            yield item

                    elif verbose and poll_count % 5 == 0:
                        # Show periodic "no events" message in verbose mode
                        elapsed = datetime.now(UTC) - start_poll_time
                        logger.info(f"No new events found after {elapsed.total_seconds():.0f}s")

                except Exception as poll_error:
                    # Only show polling errors in verbose mode
                    if verbose:
                        logger.error(f"Error polling for audit items: {poll_error}")
                    # Continue polling even if one poll fails
                    time.sleep(poll_interval)
                    continue

                # Wait for next poll
                time.sleep(poll_interval)

        except KeyboardInterrupt:
            if verbose:
                logger.info("Streaming interrupted by user")
            return
        except Exception as e:
            error = AuditError(f"Failed to stream audit logs: {str(e)}")
            capture_exception(error)
            raise error

    def describe(
        self,
        audit_id: str,
    ) -> Union[Dict[str, Any], str]:
        """
        Show detailed information about a specific audit event.

        Args:
            audit_id: The ID of the audit event to describe

        Returns:
            Dictionary containing detailed audit event information

        Raises:
            AuditError: If the audit event cannot be retrieved
            ValueError: If audit_id is not provided
        """
        try:
            if not audit_id:
                raise ValueError("audit_id is required")

            # Try to get the specific audit item by ID
            endpoint = self._format_endpoint(Endpoints.AUDIT_GET, audit_id=audit_id)

            try:
                response = self._get(endpoint=endpoint)

                if hasattr(response, 'json'):
                    try:
                        result = response.json()
                    except:
                        error = AuditError("Failed to parse audit event response")
                        capture_exception(error)
                        raise error
                else:
                    result = response

                return result

            except Exception as direct_get_error:
                # If direct GET fails, try searching through recent items
                logger.warning(f"Direct audit get failed, searching through recent items: {direct_get_error}")

                # Search through recent items (last 7 days)
                search_start_time = (datetime.now(UTC) - timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%SZ')

                query = self._build_audit_query(
                    start_time=search_start_time,
                    page=1,
                    page_size=1000,  # Large page size to search more items
                    sort_direction="desc"
                )

                endpoint = self._build_audit_endpoint(Endpoints.AUDIT_LIST, query)
                response = self._get(endpoint=endpoint)

                if hasattr(response, 'json'):
                    try:
                        search_result = response.json()
                    except:
                        error = AuditError("Failed to parse audit search response")
                        capture_exception(error)
                        raise error
                else:
                    search_result = response

                # Search for the item with matching ID
                items = search_result.get('items', []) if isinstance(search_result, dict) else search_result

                for item in items:
                    # Check various potential ID fields
                    if (item.get('id') == audit_id or
                            item.get('audit_id') == audit_id or
                            item.get('event_id') == audit_id or
                            str(item.get('timestamp')) == audit_id):
                        return item

                # If not found
                error = AuditError(f"Audit event with ID '{audit_id}' not found")
                capture_exception(error)
                raise error

        except Exception as e:
            if isinstance(e, (AuditError, ValueError)):
                raise e
            error = AuditError(f"Failed to describe audit event: {str(e)}")
            capture_exception(error)
            raise error

    def search(
        self,
        text: Optional[str] = None,
        category_type: Optional[str] = None,
        category_name: Optional[str] = None,
        resource_type: Optional[str] = None,
        action_type: Optional[str] = None,
        session_id: Optional[str] = None,
        status: Optional[str] = None,  # 'success', 'failed', or None
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
        sort_direction: str = "desc",
    ) -> Union[Dict[str, Any], str]:
        """
        Search for audit logs containing specific text or matching criteria.

        Args:
            text: Text to search for in audit logs
            category_type: Filter by category type
            category_name: Filter by category name
            resource_type: Filter by resource type
            action_type: Filter by action type
            session_id: Filter by session ID
            status: Filter by status ('success', 'failed', or None)
            start_time: Start time in RFC3339 format (default: 24 hours ago)
            end_time: End time in RFC3339 format
            page: Page number for pagination
            page_size: Number of items per page
            sort_direction: Sort direction ('asc' or 'desc')

        Returns:
            Dictionary containing:
            - items: List of matching audit log entries
            - search_summary: Summary of search criteria
            - pagination: Pagination information

        Raises:
            AuditError: If the search fails
        """
        try:
            # Set default time range if not provided (last 24 hours)
            if not start_time:
                start_time = (datetime.now(UTC) - timedelta(hours=24)).strftime('%Y-%m-%dT%H:%M:%SZ')

            # Validate time formats
            if start_time:
                self._validate_time_format(start_time)
            if end_time:
                self._validate_time_format(end_time)

            # Build base query
            query = self._build_audit_query(
                category_type=category_type,
                category_name=category_name,
                resource_type=resource_type,
                action_type=action_type,
                session_id=session_id,
                start_time=start_time,
                end_time=end_time,
                page=page,
                page_size=page_size,
                sort_direction=sort_direction
            )

            # Add search-specific parameters
            if text:
                query['search_text'] = text
            if status:
                if status not in ['success', 'failed']:
                    raise ValueError("Status must be 'success' or 'failed'")
                query['status_filter'] = status

            # Make the request
            endpoint = self._build_audit_endpoint(Endpoints.AUDIT_LIST, query)
            response = self._get(endpoint=endpoint)

            # Handle response
            if hasattr(response, 'json'):
                try:
                    result = response.json()
                except:
                    error = AuditError("Failed to parse audit search response")
                    capture_exception(error)
                    raise error
            else:
                result = response

            # If the API doesn't support text search directly, filter on client side
            if text and isinstance(result, dict) and 'items' in result:
                result['items'] = self._filter_items_by_text(result['items'], text)
            elif text and isinstance(result, list):
                result = self._filter_items_by_text(result, text)

            # Apply status filter on client side if needed
            if status and isinstance(result, dict) and 'items' in result:
                result['items'] = self._filter_items_by_status(result['items'], status)
            elif status and isinstance(result, list):
                result = self._filter_items_by_status(result, status)

            # Add search summary
            if isinstance(result, dict):
                result['search_summary'] = {
                    'text': text,
                    'status': status,
                    'category_type': category_type,
                    'time_range': {'start': start_time, 'end': end_time}
                }

            return result

        except Exception as e:
            if isinstance(e, (AuditError, ValueError)):
                raise e
            error = AuditError(f"Failed to search audit logs: {str(e)}")
            capture_exception(error)
            raise error

    # Private helper methods

    def _build_audit_query(
        self,
        category_type: Optional[str] = None,
        category_name: Optional[str] = None,
        resource_type: Optional[str] = None,
        action_type: Optional[str] = None,
        session_id: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
        sort_direction: str = "desc"
    ) -> Dict[str, Any]:
        """Build audit query parameters"""
        query = {
            "filter": {},
            "page": page,
            "page_size": page_size,
            "sort": {
                "timestamp": -1 if sort_direction == "desc" else 1
            }
        }

        # Add filters
        if category_type:
            query["filter"]["category_type"] = category_type
        if category_name:
            query["filter"]["category_name"] = category_name
        if resource_type:
            query["filter"]["resource_type"] = resource_type
        if action_type:
            query["filter"]["action_type"] = action_type
        if session_id:
            query["filter"]["session_id"] = session_id

        # Add timestamp filter
        if start_time or end_time:
            timestamp_filter = {}
            if start_time:
                timestamp_filter["gte"] = start_time
            if end_time:
                timestamp_filter["lte"] = end_time
            query["filter"]["timestamp"] = timestamp_filter

        return query

    def _validate_time_format(self, time_str: str):
        """Validate RFC3339 time format"""
        try:
            datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError(
                f"Invalid time format: {time_str}. Please use RFC3339 format (e.g., '2023-04-01T00:00:00Z')")

    def _filter_items_by_text(self, items: List[Dict[str, Any]], text: str) -> List[Dict[str, Any]]:
        """Filter items by text search (case-insensitive)"""
        text_lower = text.lower()
        filtered_items = []

        for item in items:
            # Search in all string fields of the item
            item_str = json.dumps(item, default=str).lower()
            if text_lower in item_str:
                filtered_items.append(item)

        return filtered_items

    def _filter_items_by_status(self, items: List[Dict[str, Any]], status: str) -> List[Dict[str, Any]]:
        """Filter items by success/failure status"""
        filtered_items = []

        for item in items:
            action_successful = item.get('action_successful')
            if status == 'success' and action_successful is True:
                filtered_items.append(item)
            elif status == 'failed' and action_successful is False:
                filtered_items.append(item)

        return filtered_items

    def _build_audit_endpoint(self, base_endpoint: str, query: Dict[str, Any]) -> str:
        """Build audit endpoint with query parameters"""
        import urllib.parse

        params = {}

        # Add filter as JSON string
        if query.get('filter'):
            params['filter'] = json.dumps(query['filter'])

        # Add sort as JSON string
        if query.get('sort'):
            params['sort'] = json.dumps(query['sort'])

        # Add pagination parameters
        if 'page' in query:
            params['page'] = str(query['page'])
        if 'page_size' in query:
            params['page_size'] = str(query['page_size'])

        # Add other direct parameters
        for key in ['timeout_minutes', 'verbose', 'search_text', 'status_filter']:
            if key in query:
                params[key] = str(query[key])

        # Build query string
        query_string = urllib.parse.urlencode(params)

        if query_string:
            return f"{base_endpoint}?{query_string}"
        else:
            return base_endpoint
