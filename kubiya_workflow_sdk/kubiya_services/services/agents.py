"""
Agent service for managing Kubiya agents
"""
import logging
from typing import Optional, Dict, Any, List

from kubiya_workflow_sdk import capture_exception
from kubiya_workflow_sdk.kubiya_services.constants import Endpoints
from kubiya_workflow_sdk.kubiya_services.exceptions import AgentError, ValidationError
from kubiya_workflow_sdk.kubiya_services.services.base import BaseService

logger = logging.getLogger(__name__)


class _Access:
    """Service for managing agent access control"""

    def __init__(self, agent_service):
        """
        Initialize Access service with reference to AgentService

        Args:
            agent_service: Instance of AgentService for API operations
        """
        self.agent_service = agent_service

    def show(self, agent_uuid: str) -> Dict[str, Any]:
        """
        Show current access control settings.

        Args:
            agent_uuid: UUID of the agent

        Returns:
            Dictionary containing access control information
        """
        try:
            agent = self.agent_service.get(agent_uuid)

            access_info = {
                "agent_uuid": agent_uuid,
                "agent_name": agent.get("name"),
                "owners": agent.get("owners", []),
                "allowed_users": agent.get("allowed_users", []),
                "allowed_groups": agent.get("allowed_groups", []),
                "is_open_access": len(agent.get("allowed_users", [])) == 0 and len(agent.get("allowed_groups", [])) == 0
            }

            return {"access_control": access_info, "success": True}

        except Exception as e:
            error = AgentError(f"Failed to show access for agent {agent_uuid}: {str(e)}")
            capture_exception(error)
            raise error

    def clear(self, agent_uuid: str) -> Dict[str, Any]:
        """
        Clear all access restrictions.

        Args:
            agent_uuid: UUID of the agent

        Returns:
            Dictionary containing operation result
        """
        try:
            return self.agent_service.edit(
                agent_uuid,
                allowed_users=[],
                allowed_groups=[]
            )
        except Exception as e:
            error = AgentError(f"Failed to clear access for agent {agent_uuid}: {str(e)}")
            capture_exception(error)
            raise error

    def add_user(self, agent_uuid: str, users: List[str]) -> Dict[str, Any]:
        """
        Add users to allowed list.

        Args:
            agent_uuid: UUID of the agent
            users: List of user identifiers to add

        Returns:
            Dictionary containing operation result
        """
        try:
            return self.agent_service.edit(agent_uuid, add_allowed_users=users)
        except Exception as e:
            error = AgentError(f"Failed to add users to agent {agent_uuid}: {str(e)}")
            capture_exception(error)
            raise error

    def remove_user(self, agent_uuid: str, users: List[str]) -> Dict[str, Any]:
        """
        Remove users from allowed list.

        Args:
            agent_uuid: UUID of the agent
            users: List of user identifiers to remove

        Returns:
            Dictionary containing operation result
        """
        try:
            return self.agent_service.edit(agent_uuid, remove_allowed_users=users)
        except Exception as e:
            error = AgentError(f"Failed to remove users from agent {agent_uuid}: {str(e)}")
            capture_exception(error)
            raise error

    def add_group(self, agent_uuid: str, groups: List[str]) -> Dict[str, Any]:
        """
        Add groups to allowed list.

        Args:
            agent_uuid: UUID of the agent
            groups: List of group identifiers to add

        Returns:
            Dictionary containing operation result
        """
        try:
            return self.agent_service.edit(agent_uuid, add_allowed_groups=groups)
        except Exception as e:
            error = AgentError(f"Failed to add groups to agent {agent_uuid}: {str(e)}")
            capture_exception(error)
            raise error

    def remove_group(self, agent_uuid: str, groups: List[str]) -> Dict[str, Any]:
        """
        Remove groups from allowed list.

        Args:
            agent_uuid: UUID of the agent
            groups: List of group identifiers to remove

        Returns:
            Dictionary containing operation result
        """
        try:
            return self.agent_service.edit(agent_uuid, remove_allowed_groups=groups)
        except Exception as e:
            error = AgentError(f"Failed to remove groups from agent {agent_uuid}: {str(e)}")
            capture_exception(error)
            raise error


class _Env:
    """Service for managing agent environment variables"""

    def __init__(self, agent_service):
        """
        Initialize Env service with reference to AgentService

        Args:
            agent_service: Instance of AgentService for API operations
        """
        self.agent_service = agent_service

    def list(self, agent_uuid: str) -> Dict[str, Any]:
        """
        List environment variables for an agent.

        Args:
            agent_uuid: UUID of the agent

        Returns:
            Dictionary containing environment variables
        """
        try:
            agent = self.agent_service.get(agent_uuid)
            env_vars = agent.get("environment_variables", {})

            return {
                "environment_variables": env_vars,
                "count": len(env_vars),
                "success": True
            }

        except Exception as e:
            error = AgentError(f"Failed to list environment variables for agent {agent_uuid}: {str(e)}")
            capture_exception(error)
            raise error

    def set(self, agent_uuid: str, env_vars: Dict[str, str]) -> Dict[str, Any]:
        """
        Set environment variables for an agent.

        Args:
            agent_uuid: UUID of the agent
            env_vars: Environment variables to set (key-value pairs)

        Returns:
            Dictionary containing operation result
        """
        try:
            return self.agent_service.edit(agent_uuid, add_env_vars=env_vars)
        except Exception as e:
            error = AgentError(f"Failed to set environment variables for agent {agent_uuid}: {str(e)}")
            capture_exception(error)
            raise error

    def unset(self, agent_uuid: str, keys: List[str]) -> Dict[str, Any]:
        """
        Unset environment variables for an agent.

        Args:
            agent_uuid: UUID of the agent
            keys: Environment variable keys to unset

        Returns:
            Dictionary containing operation result
        """
        try:
            return self.agent_service.edit(agent_uuid, remove_env_vars=keys)
        except Exception as e:
            error = AgentError(f"Failed to unset environment variables for agent {agent_uuid}: {str(e)}")
            capture_exception(error)
            raise error


class _Integrations:
    """Service for managing agent integrations"""

    def __init__(self, agent_service):
        """
        Initialize Integrations service with reference to AgentService

        Args:
            agent_service: Instance of AgentService for API operations
        """
        self.agent_service = agent_service

    def list(self, agent_uuid: str) -> Dict[str, Any]:
        """
        List integrations for an agent.

        Args:
            agent_uuid: UUID of the agent

        Returns:
            Dictionary containing integrations
        """
        try:
            agent = self.agent_service.get(agent_uuid)
            integrations = agent.get("integrations", [])

            return {
                "integrations": integrations,
                "count": len(integrations),
                "success": True
            }

        except Exception as e:
            error = AgentError(f"Failed to list integrations for agent {agent_uuid}: {str(e)}")
            capture_exception(error)
            raise error

    def add(self, agent_uuid: str, integrations: List[str]) -> Dict[str, Any]:
        """
        Add integrations to an agent.

        Args:
            agent_uuid: UUID of the agent
            integrations: List of integration names to add

        Returns:
            Dictionary containing operation result
        """
        try:
            return self.agent_service.edit(agent_uuid, add_integrations=integrations)
        except Exception as e:
            error = AgentError(f"Failed to add integrations to agent {agent_uuid}: {str(e)}")
            capture_exception(error)
            raise error

    def remove(self, agent_uuid: str, integrations: List[str]) -> Dict[str, Any]:
        """
        Remove integrations from an agent.

        Args:
            agent_uuid: UUID of the agent
            integrations: List of integration names to remove

        Returns:
            Dictionary containing operation result
        """
        try:
            return self.agent_service.edit(agent_uuid, remove_integrations=integrations)
        except Exception as e:
            error = AgentError(f"Failed to remove integrations from agent {agent_uuid}: {str(e)}")
            capture_exception(error)
            raise error


class _Prompt:
    """Service for managing agent AI instructions/prompts"""

    def __init__(self, agent_service):
        """
        Initialize Prompt service with reference to AgentService

        Args:
            agent_service: Instance of AgentService for API operations
        """
        self.agent_service = agent_service

    def get(self, agent_uuid: str) -> Dict[str, Any]:
        """
        Get AI instructions for an agent.

        Args:
            agent_uuid: UUID of the agent

        Returns:
            Dictionary containing AI instructions
        """
        try:
            agent = self.agent_service.get(agent_uuid)
            ai_instructions = agent.get("ai_instructions", "")

            return {
                "ai_instructions": ai_instructions,
                "has_instructions": bool(ai_instructions),
                "instruction_length": len(ai_instructions),
                "success": True
            }

        except Exception as e:
            error = AgentError(f"Failed to get AI instructions for agent {agent_uuid}: {str(e)}")
            capture_exception(error)
            raise error

    def set(
        self,
        agent_uuid: str,
        content: Optional[str] = None,
        file_path: Optional[str] = None,
        url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Set AI instructions for an agent.

        Args:
            agent_uuid: UUID of the agent
            content: Prompt content to set
            file_path: Path to file containing prompt content
            url: URL to fetch prompt content from

        Returns:
            Dictionary containing operation result
        """
        try:
            instructions = self._get_content(content, file_path, url)
            return self.agent_service.edit(agent_uuid, ai_instructions=instructions)
        except Exception as e:
            error = AgentError(f"Failed to set AI instructions for agent {agent_uuid}: {str(e)}")
            capture_exception(error)
            raise error

    def append(
        self,
        agent_uuid: str,
        content: Optional[str] = None,
        file_path: Optional[str] = None,
        url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Append to AI instructions for an agent.

        Args:
            agent_uuid: UUID of the agent
            content: Prompt content to append
            file_path: Path to file containing prompt content
            url: URL to fetch prompt content from

        Returns:
            Dictionary containing operation result
        """
        try:
            current_agent = self.agent_service.get(agent_uuid)
            current_instructions = current_agent.get("ai_instructions", "")

            new_content = self._get_content(content, file_path, url)

            if current_instructions:
                combined_instructions = f"{current_instructions}\n\n{new_content}"
            else:
                combined_instructions = new_content

            return self.agent_service.edit(agent_uuid, ai_instructions=combined_instructions)
        except Exception as e:
            error = AgentError(f"Failed to append AI instructions for agent {agent_uuid}: {str(e)}")
            capture_exception(error)
            raise error

    def clear(self, agent_uuid: str) -> Dict[str, Any]:
        """
        Clear AI instructions for an agent.

        Args:
            agent_uuid: UUID of the agent

        Returns:
            Dictionary containing operation result
        """
        try:
            return self.agent_service.edit(agent_uuid, ai_instructions="")
        except Exception as e:
            error = AgentError(f"Failed to clear AI instructions for agent {agent_uuid}: {str(e)}")
            capture_exception(error)
            raise error

    def _get_content(
        self,
        content: Optional[str],
        file_path: Optional[str],
        url: Optional[str]
    ) -> str:
        """Get content from various sources."""
        if content:
            return content
        elif file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                raise ValidationError(f"Failed to read file {file_path}: {str(e)}")
        elif url:
            try:
                import requests
                response = requests.get(url)
                response.raise_for_status()
                return response.text
            except Exception as e:
                raise ValidationError(f"Failed to fetch content from URL {url}: {str(e)}")
        else:
            raise ValidationError("Content, file_path, or url must be provided")


class _Secrets:
    """Service for managing agent secrets"""

    def __init__(self, agent_service):
        """
        Initialize Secrets service with reference to AgentService

        Args:
            agent_service: Instance of AgentService for API operations
        """
        self.agent_service = agent_service

    def list(self, agent_uuid: str) -> Dict[str, Any]:
        """
        List secrets for an agent.

        Args:
            agent_uuid: UUID of the agent

        Returns:
            Dictionary containing secrets
        """
        try:
            agent = self.agent_service.get(agent_uuid)
            secrets = agent.get("secrets", [])

            return {
                "secrets": secrets,
                "count": len(secrets),
                "success": True
            }

        except Exception as e:
            error = AgentError(f"Failed to list secrets for agent {agent_uuid}: {str(e)}")
            capture_exception(error)
            raise error

    def add(self, agent_uuid: str, secrets: List[str]) -> Dict[str, Any]:
        """
        Add secrets to an agent.

        Args:
            agent_uuid: UUID of the agent
            secrets: List of secret names to add

        Returns:
            Dictionary containing operation result
        """
        try:
            return self.agent_service.edit(agent_uuid, add_secrets=secrets)
        except Exception as e:
            error = AgentError(f"Failed to add secrets to agent {agent_uuid}: {str(e)}")
            capture_exception(error)
            raise error

    def remove(self, agent_uuid: str, secrets: List[str]) -> Dict[str, Any]:
        """
        Remove secrets from an agent.

        Args:
            agent_uuid: UUID of the agent
            secrets: List of secret names to remove

        Returns:
            Dictionary containing operation result
        """
        try:
            return self.agent_service.edit(agent_uuid, remove_secrets=secrets)
        except Exception as e:
            error = AgentError(f"Failed to remove secrets from agent {agent_uuid}: {str(e)}")
            capture_exception(error)
            raise error


class _Tools:
    """Service for managing agent tools"""

    def __init__(self, agent_service):
        """
        Initialize Tools service with reference to AgentService

        Args:
            agent_service: Instance of AgentService for API operations
        """
        self.agent_service = agent_service

    def list(self, agent_uuid: str) -> Dict[str, Any]:
        """
        List tools for an agent.

        Args:
            agent_uuid: UUID of the agent

        Returns:
            Dictionary containing tools
        """
        try:
            agent = self.agent_service.get(agent_uuid)
            tools = agent.get("tools", [])

            return {
                "tools": tools,
                "count": len(tools),
                "success": True
            }

        except Exception as e:
            error = AgentError(f"Failed to list tools for agent {agent_uuid}: {str(e)}")
            capture_exception(error)
            raise error

    def add(self, agent_uuid: str, tools: List[str]) -> Dict[str, Any]:
        """
        Add tools to an agent.

        Args:
            agent_uuid: UUID of the agent
            tools: List of tool names/IDs to add

        Returns:
            Dictionary containing operation result
        """
        try:
            return self.agent_service.edit(agent_uuid, add_tools=tools)
        except Exception as e:
            error = AgentError(f"Failed to add tools to agent {agent_uuid}: {str(e)}")
            capture_exception(error)
            raise error

    def remove(self, agent_uuid: str, tools: List[str]) -> Dict[str, Any]:
        """
        Remove tools from an agent.

        Args:
            agent_uuid: UUID of the agent
            tools: List of tool names/IDs to remove

        Returns:
            Dictionary containing operation result
        """
        try:
            return self.agent_service.edit(agent_uuid, remove_tools=tools)
        except Exception as e:
            error = AgentError(f"Failed to remove tools from agent {agent_uuid}: {str(e)}")
            capture_exception(error)
            raise error

    def describe(self, agent_uuid: str, tool_name: str) -> Dict[str, Any]:
        """
        Describe a tool for an agent.

        Args:
            agent_uuid: UUID of the agent
            tool_name: Specific tool name to describe

        Returns:
            Dictionary containing tool description
        """
        try:
            # This would need to call a tool describe endpoint
            # For now, return basic info
            return {
                "tool_name": tool_name,
                "agent_uuid": agent_uuid,
                "success": True,
                "message": f"Tool description for {tool_name} (implementation needed)"
            }
        except Exception as e:
            error = AgentError(f"Failed to describe tool {tool_name} for agent {agent_uuid}: {str(e)}")
            capture_exception(error)
            raise error


class AgentService(BaseService):
    """Service for managing Kubiya agents"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.access = _Access(self)
        self.env = _Env(self)
        self.integrations = _Integrations(self)
        self.prompt = _Prompt(self)
        self.secrets = _Secrets(self)
        self.tools = _Tools(self)

    def list(
        self,
        sort_by: str = "name",
        filter_term: str = "",
        limit: int = 100,
        show_active: bool = False
    ) -> Dict[str, Any]:
        """
        List all agents with filtering, sorting, and pagination support.

        Args:
            sort_by: Sort by field (name, created, updated)
            filter_term: Filter agents (supports partial matching)
            limit: Limit number of results
            show_active: Show only active agents

        Returns:
            Dictionary containing agents list and metadata
        """
        try:
            # Get agents from API
            endpoint = self._format_endpoint(Endpoints.AGENTS_LIST)
            agents = self._get(endpoint).json()

            # Apply filtering if requested
            if filter_term:
                filter_lower = filter_term.lower()
                filtered = []
                for agent in agents:
                    if (filter_lower in agent.get('name', '').lower() or
                            filter_lower in agent.get('description', '').lower() or
                            filter_lower in agent.get('instruction_type', '').lower() or
                            filter_lower in agent.get('llm_model', '').lower()):
                        filtered.append(agent)
                        continue

                    # Check sources, integrations
                    for integration in agent.get('integrations', []):
                        if filter_lower in integration.lower():
                            filtered.append(agent)
                            break

                agents = filtered

            # Apply active filter if requested
            if show_active:
                # Filter based on agent status - this logic would need to be implemented
                # based on your specific criteria for "active" agents
                active_agents = []
                for agent in agents:
                    # Example criteria - adjust based on your requirements
                    if agent.get('runners') and len(agent.get('sources', [])) > 0:
                        active_agents.append(agent)
                agents = active_agents

            # Apply sorting
            if sort_by == "name":
                agents.sort(key=lambda x: x.get('name', '').lower())
            elif sort_by == "created":
                agents.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            elif sort_by == "updated":
                agents.sort(key=lambda x: x.get('updated_at', ''), reverse=True)

            # Apply limit
            if limit > 0:
                agents = agents[:limit]

            return agents

        except Exception as e:
            error = AgentError(f"Failed to list agents: {str(e)}")
            capture_exception(error)
            raise error

    def get(self, agent_uuid: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific agent.

        Args:
            agent_uuid: UUID of the agent to retrieve

        Returns:
            Dictionary containing agent details
        """
        try:
            endpoint = self._format_endpoint(Endpoints.AGENT_GET, agent_uuid=agent_uuid)
            return self._get(endpoint).json()

        except Exception as e:
            error = AgentError(f"Failed to get agent {agent_uuid}: {str(e)}")
            capture_exception(error)
            raise error

    def create(
        self,
        name: str,
        description: str = "",
        llm_model: str = "claude-4-sonnet",
        instruction_type: str = "natural_language",
        sources: Optional[List[str]] = None,
        secrets: Optional[List[str]] = None,
        integrations: Optional[List[str]] = None,
        environment: Optional[Dict[str, str]] = None,
        runners: Optional[List[str]] = None,
        ai_instructions: str = "",
        is_debug_mode: bool = False,
        owners: Optional[List[str]] = None,
        allowed_users: Optional[List[str]] = None,
        allowed_groups: Optional[List[str]] = None,
        tools: Optional[List[str]] = None,
        image: str = "ghcr.io/kubiyabot/kubiya-agent:stable",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a new agent.

        Args:
            name: Agent name (required)
            description: Agent description
            llm_model: LLM model to use
            instruction_type: Type of instructions
            sources: List of source UUIDs to attach
            secrets: List of secret names to attach
            integrations: List of integrations to attach
            environment: Environment variables dict
            runners: List of runner names
            ai_instructions: Custom AI instructions
            is_debug_mode: Enable debug mode
            owners: List of owner identifiers
            allowed_users: List of allowed user identifiers
            allowed_groups: List of allowed group identifiers
            tools: List of tool identifiers
            image: Docker image for the agent
            **kwargs: Additional agent properties

        Returns:
            Dictionary containing created agent details
        """
        try:

            # Prepare agent data
            agent_data = {
                "name": name,
                "description": description,
                "llm_model": llm_model,
                "instruction_type": instruction_type,
                "sources": sources or [],
                "secrets": secrets or [],
                "integrations": integrations or [],
                "environment_variables": environment or {},
                "runners": runners or ["gke-poc-kubiya"],
                "ai_instructions": ai_instructions,
                "is_debug_mode": is_debug_mode,
                "owners": owners or [],
                "allowed_users": allowed_users or [],
                "allowed_groups": allowed_groups or [],
                "tools": tools or [],
                "image": image,
                "managed_by": "",
                "links": [],
                "tasks": [],
                "tags": [],
                **kwargs
            }

            endpoint = self._format_endpoint(Endpoints.AGENT_CREATE)
            return self._post(endpoint, data=agent_data, stream=False).json()

        except Exception as e:
            error = AgentError(f"Failed to create agent: {str(e)}")
            capture_exception(error)
            raise error

    def delete(self, agent_uuid: str) -> Dict[str, Any]:
        """
        Delete an agent.

        Args:
            agent_uuid: UUID of the agent to delete

        Returns:
            Dictionary containing deletion status
        """
        try:
            endpoint = self._format_endpoint(Endpoints.AGENT_DELETE, agent_uuid=agent_uuid)
            self._delete(endpoint).json()

            return {
                "success": True,
                "message": f"Successfully deleted agent: {agent_uuid}"
            }

        except Exception as e:
            error = AgentError(f"Failed to delete agent {agent_uuid}: {str(e)}")
            capture_exception(error)
            raise error

    def edit(
        self,
        agent_uuid: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        llm_model: Optional[str] = None,
        ai_instructions: Optional[str] = None,
        add_sources: Optional[List[str]] = None,
        remove_sources: Optional[List[str]] = None,
        add_secrets: Optional[List[str]] = None,
        remove_secrets: Optional[List[str]] = None,
        add_env_vars: Optional[Dict[str, str]] = None,
        remove_env_vars: Optional[List[str]] = None,
        add_integrations: Optional[List[str]] = None,
        remove_integrations: Optional[List[str]] = None,
        add_tools: Optional[List[str]] = None,
        remove_tools: Optional[List[str]] = None,
        add_allowed_users: Optional[List[str]] = None,
        remove_allowed_users: Optional[List[str]] = None,
        add_allowed_groups: Optional[List[str]] = None,
        remove_allowed_groups: Optional[List[str]] = None,
        runners: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Edit an existing agent.

        Args:
            agent_uuid: UUID of the agent to edit
            name: New agent name
            description: New agent description
            llm_model: New LLM model
            ai_instructions: New AI instructions
            add_sources: Sources to add
            remove_sources: Sources to remove
            add_secrets: Secrets to add
            remove_secrets: Secrets to remove
            add_env_vars: Environment variables to add/update
            remove_env_vars: Environment variable keys to remove
            add_integrations: Integrations to add
            remove_integrations: Integrations to remove
            add_tools: Tools to add
            remove_tools: Tools to remove
            add_allowed_users: Users to add to allowed list
            remove_allowed_users: Users to remove from allowed list
            add_allowed_groups: Groups to add to allowed list
            remove_allowed_groups: Groups to remove from allowed list
            runners: List of runners to set
            **kwargs: Additional fields to update

        Returns:
            Dictionary containing updated agent details
        """
        try:
            # Get current agent state
            current_agent = self.get(agent_uuid)

            # Update basic fields if provided
            if name is not None:
                current_agent["name"] = name
            if description is not None:
                current_agent["description"] = description
            if llm_model is not None:
                current_agent["llm_model"] = llm_model
            if ai_instructions is not None:
                current_agent["ai_instructions"] = ai_instructions
            if runners is not None:
                current_agent["runners"] = runners

            # Handle list additions and removals
            self._update_list_field(current_agent, "sources", add_sources, remove_sources)
            self._update_list_field(current_agent, "secrets", add_secrets, remove_secrets)
            self._update_list_field(current_agent, "integrations", add_integrations, remove_integrations)
            self._update_list_field(current_agent, "tools", add_tools, remove_tools)
            self._update_list_field(current_agent, "allowed_users", add_allowed_users, remove_allowed_users)
            self._update_list_field(current_agent, "allowed_groups", add_allowed_groups, remove_allowed_groups)

            # Handle environment variables
            if add_env_vars or remove_env_vars:
                env_vars = current_agent.get("environment_variables", {})
                if env_vars is None:
                    env_vars = {}

                if add_env_vars:
                    env_vars.update(add_env_vars)

                if remove_env_vars:
                    for key in remove_env_vars:
                        env_vars.pop(key, None)

                current_agent["environment_variables"] = env_vars

            # Ensure environment_variables is not None to avoid 500 errors
            if current_agent.get("environment_variables") is None:
                current_agent["environment_variables"] = {}

            # Create complete update payload matching
            # Exclude problematic fields like "id", "desc", "uuid", "metadata"
            update_data = {
                "name": current_agent.get("name"),
                "description": current_agent.get("description"),
                "instruction_type": current_agent.get("instruction_type"),
                "llm_model": current_agent.get("llm_model"),
                "sources": current_agent.get("sources", []),
                "environment_variables": current_agent.get("environment_variables", {}),
                "secrets": current_agent.get("secrets", []),
                "allowed_groups": current_agent.get("allowed_groups", []),
                "allowed_users": current_agent.get("allowed_users", []),
                "owners": current_agent.get("owners", []),
                "runners": current_agent.get("runners", []),
                "is_debug_mode": current_agent.get("is_debug_mode", False),
                "ai_instructions": current_agent.get("ai_instructions", ""),
                "image": current_agent.get("image", ""),
                "managed_by": current_agent.get("managed_by", ""),
                "integrations": current_agent.get("integrations", []),
                "links": current_agent.get("links", []),
                "tools": current_agent.get("tools", []),
                "tasks": current_agent.get("tasks", []),
                "tags": current_agent.get("tags", [])
            }

            # Apply any additional kwargs to the update data
            for key, value in kwargs.items():
                if key not in ["id", "uuid", "desc", "metadata"]:  # Exclude problematic fields
                    update_data[key] = value

            # Update the agent using PUT with complete payload
            endpoint = self._format_endpoint(Endpoints.AGENT_UPDATE, agent_uuid=agent_uuid)
            return self._put(endpoint, data=update_data).json()

        except Exception as e:
            error = AgentError(f"Failed to edit agent {agent_uuid}: {str(e)}")
            capture_exception(error)
            raise error

    def model(self, agent_uuid: str, llm_model: str) -> Dict[str, Any]:
        """
        Set the LLM model for an agent.

        Args:
            agent_uuid: UUID of the agent
            llm_model: LLM model to set (claude-4-sonnet, claude-4-opus, gpt-4o)

        Returns:
            Dictionary containing operation result
        """
        try:
            # Validate model
            supported_models = ["claude-4-sonnet", "claude-4-opus", "gpt-4o"]
            if llm_model not in supported_models:
                raise ValidationError(f"Unsupported model: {llm_model}. Supported: {', '.join(supported_models)}")

            return self.edit(agent_uuid, llm_model=llm_model)

        except Exception as e:
            error = AgentError(f"Failed to set model for agent {agent_uuid}: {str(e)}")
            capture_exception(error)
            raise error

    def runner(self, agent_uuid: str, runner_name: str) -> Dict[str, Any]:
        """
        Set the runner for an agent.

        Args:
            agent_uuid: UUID of the agent
            runner_name: Name of the runner to set

        Returns:
            Dictionary containing operation result
        """
        try:
            return self.edit(agent_uuid, runners=[runner_name])

        except Exception as e:
            error = AgentError(f"Failed to set runner for agent {agent_uuid}: {str(e)}")
            capture_exception(error)
            raise error

    def _update_list_field(
        self,
        data: Dict[str, Any],
        field_name: str,
        add_items: Optional[List[str]],
        remove_items: Optional[List[str]]
    ) -> None:
        """Update a list field by adding and removing items."""
        current_list = data.get(field_name, [])

        if add_items:
            # Add new items (avoid duplicates)
            for item in add_items:
                if item not in current_list:
                    current_list.append(item)

        if remove_items:
            # Remove items
            current_list = [item for item in current_list if item not in remove_items]

        data[field_name] = current_list
