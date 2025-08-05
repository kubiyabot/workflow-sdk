"""
Step builder with support for all executor types and features.

Properly handles:
- Tool executors with full definitions or references
- Inline agent executors
- Docker, shell, python, http, ssh executors
- All step features: retry, conditions, outputs, etc.
"""

from typing import Dict, Any, List, Optional, Union


class Step:
    """
    Step builder with fluent API.

    Example with tool definition:
        step = (Step("notify")
                .tool_def(
                    name="slack-notifier",
                    type="docker",
                    image="curlimages/curl:latest",
                    content="#!/bin/sh\\ncurl -X POST...",
                    args=[{"name": "channel", "type": "string"}]
                )
                .args(channel="#alerts", message="Error!"))

    Example with inline agent:
        step = (Step("analyze")
                .inline_agent(
                    message="Analyze this incident: {{incident}}",
                    agent_name="incident-analyzer",
                    ai_instructions="You are an SRE expert...",
                    llm_model="gpt-4o"
                ))
    """

    def __init__(
        self,
        name: str,
        command: Optional[str] = None,
        description: Optional[str] = None,
        script: Optional[str] = None,
        run: Optional[str] = None,
        params: Optional[str] = None,
        **kwargs,
    ):
        self.data = {"name": name}

        if command:
            self.data["command"] = command
            self.data["executor"] = {"type": "command", "config": {}}
        if description:
            self.data["description"] = description
        if script:
            self.data["script"] = script
        if run:
            self.data["run"] = run
        if params:
            self.data["params"] = params

        # Apply any additional kwargs
        for key, value in kwargs.items():
            if value is not None:
                self.data[key] = value

    def description(self, desc: str) -> "Step":
        """Set step description."""
        self.data["description"] = desc
        return self

    # Executor configurations
    def shell(self, command: str, with_config: bool = True, **config) -> "Step":
        """Configure as shell executor."""
        self.data["command"] = command
        if with_config:
            self.data["executor"] = {"type": "command", "config": config}
        return self

    def python(self, script: str) -> "Step":
        """Configure as Python script."""
        self.data["command"] = "python"
        self.data["script"] = script
        return self

    def script(self, script: str) -> "Step":
        """Configure as a script."""
        self.data["script"] = script
        return self

    def docker(
        self, image: str, command: Optional[str] = None, content: Optional[str] = None
    ) -> "Step":
        """Configure as Docker executor."""
        executor = {"type": "docker", "config": {"image": image}}
        if command:
            executor["config"]["command"] = command
        if content:
            executor["config"]["content"] = content
        self.data["executor"] = executor
        return self

    def tool_def(
        self,
        name: str,
        type: str,
        image: str,
        content: str,
        args: Dict[str, Any],
        config_args: List[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        description: Optional[str] = None,
        with_files: Optional[List[Dict[str, str]]] = None,
        with_services: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> "Step":
        """Define a tool inline with full specification and optional bounded services."""
        tool_def = {"name": name, "type": type, "image": image, "content": content}

        if description:
            tool_def["description"] = description
        if with_files:
            tool_def["with_files"] = with_files
        if with_services:
            tool_def["with_services"] = with_services
        if config_args:
            tool_def["args"] = config_args

        tool_def = tool_def | kwargs

        self.data["executor"] = {"type": "tool", "config": {"tool_def": tool_def, "args": args}}

        if timeout:
            self.data["executor"]["config"]["timeout"] = timeout

        return self

    def tool(self, tool_name: str, args: Optional[Dict[str, Any]] = None, **kwargs) -> "Step":
        """Use a pre-registered tool."""
        config = {"tool_name": tool_name}
        if args:
            config["args"] = args

        self.data["executor"] = {"type": "tool", "config": config}
        return self

    def inline_agent(
            self,
            message: str,
            agent_name: str,
            ai_instructions: str,
            runners: List[str],
            llm_model: str = "gpt-4o-mini",
            description: Optional[str] = None,
            is_debug_mode: bool = True,
            tools: Optional[List[Dict[str, Any]]] = None,
    ) -> "Step":
        """Configure as inline agent executor."""
        agent_config = {
            "name": agent_name,
            "ai_instructions": ai_instructions,
            "runners": runners,
            "llm_model": llm_model,
            "is_debug_mode": is_debug_mode,
        }

        if description:
            agent_config["description"] = description
        if tools:
            agent_config["tools"] = tools

        self.data["executor"] = {
            "type": "inline_agent",
            "config": {"message": message, "agent": agent_config},
        }
        return self

    def agent(
        self,
        message: str,
        name: str,
        runners: List[str] = None,
        llm_model: Optional[str] = None,
        ai_instructions: Optional[str] = None,
        description: Optional[str] = None,
        is_debug_mode: bool = False,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> "Step":
        """Configure as inline agent executor."""
        agent_config = {
            "agent_name": name,
            "message": message,
        }
        if runners:
            agent_config["runners"] = runners
        if llm_model:
            agent_config["llm_model"] = llm_model
        if ai_instructions:
            agent_config["ai_instructions"] = ai_instructions
        if description:
            agent_config["description"] = description
        if is_debug_mode:
            agent_config["is_debug_mode"] = is_debug_mode
        if tools:
            agent_config["tools"] = tools

        self.data["executor"] = {
            "type": "agent",
            "config": agent_config,
        }
        return self

    def http(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Any] = None,
    ) -> "Step":
        """Configure as HTTP executor."""
        config = {"url": url, "method": method}
        if headers:
            config["headers"] = headers
        if body:
            config["body"] = body

        self.data["executor"] = {"type": "http", "config": config}
        return self

    def ssh(
        self, host: str, user: str, command: str, port: int = 22, key_file: Optional[str] = None
    ) -> "Step":
        """Configure as SSH executor."""
        config = {"host": host, "user": user, "command": command, "port": port}
        if key_file:
            config["keyFile"] = key_file

        self.data["executor"] = {"type": "ssh", "config": config}
        return self

    def llm_completion(
        self,
        api_key: str = None,
        messages: List[Dict[str, str]] = None,
        model: str = "gpt-4o",
        evaluate:bool = True,
        temperature: float = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[int] = None,
        system_prompt: Optional[str] = None,
        prompt: Optional[str] = None,
        json_mode: bool = False,
    ) -> "Step":
        """Configure as llm_completion executor."""
        executor = {
            "type": "llm_completion",
            "config": {
                "model": model,
                "evaluate": evaluate,
            }
        }
        if api_key:
            executor["config"]["api_key"] = api_key
        if messages:
            executor["config"]["messages"] = messages
        if temperature:
            executor["config"]["temperature"] = temperature
        if max_tokens:
            executor["config"]["max_tokens"] = max_tokens
        if timeout:
            executor["config"]["timeout"] = timeout
        if prompt:
            executor["config"]["prompt"] = prompt
        if system_prompt:
            executor["config"]["system_prompt"] = system_prompt
        if json_mode:
            executor["config"]["json_mode"] = json_mode

        self.data["executor"] = executor
        return self

    def kubiya(self, url: str, method: str = "GET", **config) -> "Step":
        """Configure as Kubiya API executor."""
        self.data["executor"] = {
            "type": "kubiya",
            "config": {"url": url, "method": method, **config},
        }
        return self

    def jq(self, query: Optional[str]) -> "Step":
        """Configure as jq executor for JSON processing."""
        config = dict()
        if query is None:
            config["query"] = query
        self.data["executor"] = {"type": "jq", "config": config}
        return self

    # Tool/executor arguments
    def args(self, **arguments) -> "Step":
        """Set arguments for tool executors."""
        if "executor" not in self.data:
            self.data["executor"] = {"type": "tool", "config": {}}

        if "config" not in self.data["executor"]:
            self.data["executor"]["config"] = {}

        self.data["executor"]["config"]["args"] = arguments
        return self

    # Dependencies
    def depends(self, *dependencies: Union[str, List[str]]) -> "Step":
        """Set step dependencies."""
        deps = []
        for dep in dependencies:
            if isinstance(dep, list):
                deps.extend(dep)
            else:
                deps.append(dep)

        if deps:
            self.data["depends"] = deps
        return self

    # Parallel execution
    def parallel(
        self, items: Union[List[Any], str], max_concurrent: Optional[int] = None
    ) -> "Step":
        """Configure parallel execution."""
        if isinstance(items, str):
            # Reference to variable
            self.data["parallel"] = items
        else:
            parallel_config = {"items": items}
            if max_concurrent:
                parallel_config["maxConcurrent"] = max_concurrent
            self.data["parallel"] = parallel_config
        return self

    # Data handling
    def output(self, name: str) -> "Step":
        """Capture output to variable."""
        self.data["output"] = name
        return self

    def stdout(self, file_path: str) -> "Step":
        """Redirect stdout to file."""
        self.data["stdout"] = file_path
        return self

    def stderr(self, file_path: str) -> "Step":
        """Redirect stderr to file."""
        self.data["stderr"] = file_path
        return self

    def env(self, variables: Optional[Dict[str, str]] = None, **kwargs) -> "Step":
        """Set environment variables."""
        env_vars = variables or {}
        env_vars.update(kwargs)

        if env_vars:
            self.data["env"] = env_vars
        return self

    def dir(self, working_dir: str) -> "Step":
        """Set working directory."""
        self.data["dir"] = working_dir
        return self

    def shell_type(self, shell: str) -> "Step":
        """Set shell type (bash, sh, etc)."""
        self.data["shell"] = shell
        return self

    def id(self, identifier: str) -> "Step":
        """Set step ID for referencing."""
        self.data["id"] = identifier
        return self

    # Control flow
    def preconditions(self, *conditions: Union[str, Dict[str, str]]) -> "Step":
        """Add execution preconditions."""
        self.data["preconditions"] = list(conditions)
        return self

    def retry(
        self,
        limit: int = 3,
        interval_sec: int = 30,
        max_interval_sec: Optional[int] = None,
        exponential_base: float = 2.0,
        exit_codes: Optional[List[int]] = None,
        retry_on: Optional[List[str]] = None,
        backoff: float = None
    ) -> "Step":
        """Configure retry policy."""
        retry_policy = {"limit": limit, "intervalSec": interval_sec}

        if max_interval_sec:
            retry_policy["maxIntervalSec"] = max_interval_sec
        if exponential_base != 2.0:
            retry_policy["exponentialBase"] = exponential_base
        if exit_codes:
            retry_policy["exitCodes"] = exit_codes
        if retry_on:
            retry_policy["retryOn"] = retry_on
        if backoff:
            retry_policy["backoff"] = backoff

        self.data["retryPolicy"] = retry_policy
        return self

    def repeat(
        self,
        interval_sec: int = 60,
        limit: Optional[int] = None,
        exit_code: Optional[List[int]] = None,
        condition: Optional[str] = None,
        expected: Optional[str] = None,
    ) -> "Step":
        """Configure repeat policy."""
        repeat_policy = {"intervalSec": interval_sec}

        if limit:
            repeat_policy["limit"] = limit
        elif exit_code:
            repeat_policy["exitCode"] = exit_code
        elif condition and expected:
            repeat_policy["condition"] = condition
            repeat_policy["expected"] = expected
        else:
            repeat_policy["repeat"] = True

        self.data["repeatPolicy"] = repeat_policy
        return self

    def continue_on(
        self,
        failure: bool = False,
        exit_code: Optional[List[int]] = None,
        output: Optional[Union[str, List[str]]] = None,
        mark_success: bool = False,
    ) -> "Step":
        """Configure continue-on conditions."""
        continue_config = {}

        if failure is not None:
            continue_config["failure"] = failure
        if exit_code:
            continue_config["exitCode"] = exit_code
        if output:
            continue_config["output"] = output
        if mark_success is not None:
            continue_config["markSuccess"] = mark_success

        if continue_config:
            self.data["continueOn"] = continue_config
        return self

    def timeout(self, seconds: int) -> "Step":
        """Set step timeout."""
        self.data["timeout"] = seconds
        return self

    def retries(self, count: int) -> "Step":
        """Set step timeout."""
        self.data["retries"] = int(count)
        return self

    def signal_on_stop(self, signal: str = "SIGTERM") -> "Step":
        """Set signal to send on stop."""
        self.data["signalOnStop"] = signal
        return self

    def mail_on_error(self, send: bool = True) -> "Step":
        """Send email on error."""
        self.data["mailOnError"] = send
        return self

    # Service management for tools
    def with_service(
        self,
        name: str,
        image: str,
        exposed_ports: Optional[List[int]] = None,
        env: Optional[Dict[str, str]] = None,
        entrypoint: Optional[List[str]] = None,
        volumes: Optional[List[Dict[str, str]]] = None,
    ) -> "Step":
        """Add a bounded service to this tool step."""
        service_spec = {"name": name, "image": image}

        if exposed_ports:
            service_spec["exposed_ports"] = exposed_ports
        if env:
            service_spec["env"] = env
        if entrypoint:
            service_spec["entrypoint"] = entrypoint
        if volumes:
            service_spec["with_volumes"] = volumes

        # Ensure we have a tool executor with services support
        if "executor" not in self.data:
            self.data["executor"] = {"type": "tool", "config": {"tool_def": {}}}
        elif self.data["executor"]["type"] != "tool":
            raise ValueError("Services can only be added to tool executors")

        tool_def = self.data["executor"]["config"].get("tool_def", {})
        if "with_services" not in tool_def:
            tool_def["with_services"] = []

        tool_def["with_services"].append(service_spec)
        self.data["executor"]["config"]["tool_def"] = tool_def

        return self

    def with_database(
        self,
        name: str = "database",
        db_type: str = "postgres",
        port: int = 5432,
        env: Optional[Dict[str, str]] = None,
    ) -> "Step":
        """Add a database service to this tool step."""
        images = {
            "postgres": "postgres:15-alpine",
            "mysql": "mysql:8.0",
            "mongodb": "mongo:7.0",
            "redis": "redis:7-alpine",
        }

        if db_type not in images:
            raise ValueError(f"Unsupported database type: {db_type}")

        default_env = {}
        if db_type == "postgres":
            default_env = {
                "POSTGRES_DB": "app_db",
                "POSTGRES_USER": "app_user",
                "POSTGRES_PASSWORD": "app_password",
            }
        elif db_type == "mysql":
            default_env = {
                "MYSQL_DATABASE": "app_db",
                "MYSQL_USER": "app_user",
                "MYSQL_PASSWORD": "app_password",
                "MYSQL_ROOT_PASSWORD": "root_password",
            }
        elif db_type == "mongodb":
            default_env = {
                "MONGO_INITDB_DATABASE": "app_db",
                "MONGO_INITDB_ROOT_USERNAME": "app_user",
                "MONGO_INITDB_ROOT_PASSWORD": "app_password",
            }

        # Merge with user-provided env
        final_env = {**default_env, **(env or {})}

        return self.with_service(
            name=name, image=images[db_type], exposed_ports=[port], env=final_env
        )

    def with_cache(
        self, name: str = "cache", cache_type: str = "redis", port: int = 6379
    ) -> "Step":
        """Add a cache service to this tool step."""
        images = {"redis": "redis:7-alpine", "memcached": "memcached:1.6-alpine"}

        if cache_type not in images:
            raise ValueError(f"Unsupported cache type: {cache_type}")

        return self.with_service(name=name, image=images[cache_type], exposed_ports=[port])

    def with_message_queue(
        self, name: str = "queue", queue_type: str = "rabbitmq", port: int = 5672
    ) -> "Step":
        """Add a message queue service to this tool step."""
        images = {"rabbitmq": "rabbitmq:3.12-alpine", "kafka": "confluentinc/cp-kafka:latest"}

        if queue_type not in images:
            raise ValueError(f"Unsupported queue type: {queue_type}")

        env = {}
        if queue_type == "rabbitmq":
            env = {"RABBITMQ_DEFAULT_USER": "app_user", "RABBITMQ_DEFAULT_PASS": "app_password"}

        return self.with_service(
            name=name, image=images[queue_type], exposed_ports=[port], env=env if env else None
        )

    # Conversion
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.data


# Convenience functions
def step(name: str, command: Optional[str] = None, **kwargs) -> Step:
    """Create a basic step."""
    return Step(name, command, **kwargs)


def parallel_step(
    name: str, items: List[Any], command: str, max_concurrent: Optional[int] = None, **kwargs
) -> Step:
    """Create a parallel execution step."""
    return Step(name, command, **kwargs).parallel(items, max_concurrent)


def conditional_step(
    name: str, command: str, conditions: List[Union[str, Dict[str, str]]], **kwargs
) -> Step:
    """Create a conditional step."""
    return Step(name, command, **kwargs).preconditions(*conditions)
