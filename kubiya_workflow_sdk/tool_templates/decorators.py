"""Python decorators for creating tool_templates easily."""

import inspect
import functools
from typing import Callable, Optional, Dict, Any, List, Union, TypeVar
import json
import yaml

from ..core import ToolDefinition, ToolType

T = TypeVar("T", bound=Callable[..., Any])


def tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    args: Optional[List[Dict[str, Any]]] = None,
    env: Optional[List[str]] = None,
    secrets: Optional[List[str]] = None,
    requirements: Optional[List[str]] = None,
    timeout: int = 300,
    icon_url: Optional[str] = None,
) -> Callable[[T], T]:
    """Decorator to create a Python tool from a function.

    Args:
        name: Tool name (defaults to function name)
        description: Tool description (defaults to docstring)
        args: Tool argument definitions
        env: Environment variables needed
        secrets: Secrets needed
        requirements: Python packages to install
        timeout: Execution timeout in seconds
        icon_url: Optional icon URL

    Example:
        @tool(
            name="data_processor",
            description="Process data files",
            args=[
                {"name": "input_file", "type": "string", "description": "Input file path"},
                {"name": "output_format", "type": "string", "description": "Output format", "default": "json"}
            ],
            requirements=["pandas>=1.3.0", "numpy"]
        )
        def process_data(input_file: str, output_format: str = "json") -> Dict[str, Any]:
            import pandas as pd
            df = pd.read_csv(input_file)
            # Process data...
            return {"rows": len(df), "columns": len(df.columns)}
    """

    def decorator(func: T) -> T:
        # Extract function metadata
        func_name = name or func.__name__
        func_description = description or func.__doc__ or f"Python function: {func_name}"

        # Get function source
        source = inspect.getsource(func)

        # Build requirements install command if needed
        install_cmd = ""
        if requirements:
            install_cmd = f"pip install {' '.join(requirements)}\n\n"

        # Extract function arguments if not provided
        tool_args = args
        if tool_args is None:
            sig = inspect.signature(func)
            tool_args = []
            for param_name, param in sig.parameters.items():
                arg_def = {
                    "name": param_name,
                    "type": "string",  # Default type
                    "description": f"Parameter {param_name}",
                }

                # Handle default values
                if param.default != inspect.Parameter.empty:
                    arg_def["default"] = str(param.default)
                    arg_def["required"] = False
                else:
                    arg_def["required"] = True

                # Try to infer type from annotations
                if param.annotation != inspect.Parameter.empty:
                    if param.annotation == int:
                        arg_def["type"] = "integer"
                    elif param.annotation == float:
                        arg_def["type"] = "number"
                    elif param.annotation == bool:
                        arg_def["type"] = "boolean"
                    elif param.annotation == list:
                        arg_def["type"] = "array"
                    elif param.annotation == dict:
                        arg_def["type"] = "object"

                tool_args.append(arg_def)

        # Create tool definition
        tool_def = ToolDefinition(
            name=func_name,
            description=func_description,
            type="python",
            content=install_cmd + source,
            args=tool_args,
            env=env or [],
            secrets=secrets or [],
            icon_url=icon_url,
        )

        # Add tool definition as function attribute
        func.tool_definition = tool_def
        func.as_tool = lambda: tool_def.to_dict()

        # Create execution wrapper
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        # Copy attributes
        wrapper.tool_definition = tool_def
        wrapper.as_tool = func.as_tool

        return wrapper

    return decorator


def shell_tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    args: Optional[List[Dict[str, Any]]] = None,
    env: Optional[List[str]] = None,
    secrets: Optional[List[str]] = None,
    shell: str = "/bin/bash",
) -> Callable[[T], T]:
    """Decorator to create a shell tool from a function returning shell commands.

    Args:
        name: Tool name
        description: Tool description
        args: Tool argument definitions
        env: Environment variables needed
        secrets: Secrets needed
        shell: Shell to use

    Example:
        @shell_tool(
            name="git_status",
            description="Check git repository status",
            args=[{"name": "repo_path", "type": "string", "description": "Repository path"}]
        )
        def git_status(repo_path: str) -> str:
            return f'''
            cd {repo_path}
            git status
            git log --oneline -10
            '''
    """

    def decorator(func: T) -> T:
        # Extract metadata
        func_name = name or func.__name__
        func_description = description or func.__doc__ or f"Shell script: {func_name}"

        # Create wrapper that generates shell script
        def generate_script(**kwargs):
            # Call function to get shell commands
            commands = func(**kwargs)

            # Add shebang and error handling
            script = f"""#!{shell}
set -e  # Exit on error
set -u  # Exit on undefined variable

# Generated shell script from {func_name}
{commands}
"""
            return script

        # Extract function arguments if not provided
        tool_args = args
        if tool_args is None:
            sig = inspect.signature(func)
            tool_args = []
            for param_name, param in sig.parameters.items():
                tool_args.append(
                    {
                        "name": param_name,
                        "type": "string",
                        "description": f"Parameter {param_name}",
                        "required": param.default == inspect.Parameter.empty,
                    }
                )

        # Create tool definition
        tool_def = ToolDefinition(
            name=func_name,
            description=func_description,
            type="shell",
            content=generate_script.__doc__ or "",  # Placeholder
            args=tool_args,
            env=env or [],
            secrets=secrets or [],
        )

        # Add attributes
        func.tool_definition = tool_def
        func.as_tool = lambda: tool_def.to_dict()
        func.generate_script = generate_script

        return func

    return decorator


def docker_tool(
    image: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    args: Optional[List[Dict[str, Any]]] = None,
    env: Optional[List[str]] = None,
    secrets: Optional[List[str]] = None,
    volumes: Optional[List[Dict[str, str]]] = None,
    command: Optional[str] = None,
    gpu: bool = False,
) -> Callable[[T], T]:
    """Decorator to create a Docker-based tool.

    Args:
        image: Docker image to use
        name: Tool name
        description: Tool description
        args: Tool argument definitions
        env: Environment variables needed
        secrets: Secrets needed
        volumes: Volume mounts
        command: Override container command
        gpu: Enable GPU support

    Example:
        @docker_tool(
            image="tensorflow/tensorflow:latest-gpu",
            name="ml_trainer",
            description="Train ML models",
            gpu=True,
            args=[
                {"name": "dataset", "type": "string", "description": "Dataset path"},
                {"name": "epochs", "type": "integer", "description": "Training epochs", "default": "10"}
            ]
        )
        def train_model(dataset: str, epochs: int = 10) -> str:
            return f'''
            import tensorflow as tf
            # Training logic here
            print(f"Training on {dataset} for {epochs} epochs")
            '''
    """

    def decorator(func: T) -> T:
        # Extract metadata
        func_name = name or func.__name__
        func_description = description or func.__doc__ or f"Docker tool: {func_name}"

        # Get function content
        if inspect.isfunction(func):
            # Function returns the script content
            content = func()
        else:
            content = ""

        # Create tool definition
        tool_def = ToolDefinition(
            name=func_name,
            description=func_description,
            type="docker",
            image=image,
            content=content,
            command=command,
            args=args or [],
            env=env or [],
            secrets=secrets or [],
            with_volumes=volumes or [],
        )

        # Add GPU config if needed
        if gpu:
            tool_def.config = {"gpu": True}

        # Add attributes
        func.tool_definition = tool_def
        func.as_tool = lambda: tool_def.to_dict()

        return func

    return decorator


def create_tool_from_function(
    func: Callable,
    name: Optional[str] = None,
    description: Optional[str] = None,
    tool_type: str = "python",
    **kwargs,
) -> ToolDefinition:
    """Create a tool definition from a Python function.

    Args:
        func: Python function to convert
        name: Override function name
        description: Override function docstring
        tool_type: Tool type (python, shell, docker)
        **kwargs: Additional tool configuration

    Returns:
        ToolDefinition
    """
    # Extract metadata
    func_name = name or func.__name__
    func_description = description or func.__doc__ or f"Function: {func_name}"

    # Get source code
    source = inspect.getsource(func)

    # Extract arguments
    sig = inspect.signature(func)
    args = []

    for param_name, param in sig.parameters.items():
        arg_def = {"name": param_name, "type": "string", "description": f"Parameter {param_name}"}

        if param.default != inspect.Parameter.empty:
            arg_def["default"] = str(param.default)

        args.append(arg_def)

    # Create tool definition
    return ToolDefinition(
        name=func_name,
        description=func_description,
        type=tool_type,
        content=source,
        args=args,
        **kwargs,
    )


def tool_from_yaml(yaml_str: str) -> ToolDefinition:
    """Create a tool definition from YAML string.

    Args:
        yaml_str: YAML string with tool definition

    Returns:
        ToolDefinition
    """
    data = yaml.safe_load(yaml_str)
    return ToolDefinition(**data)


def tool_from_json(json_str: str) -> ToolDefinition:
    """Create a tool definition from JSON string.

    Args:
        json_str: JSON string with tool definition

    Returns:
        ToolDefinition
    """
    data = json.loads(json_str)
    return ToolDefinition(**data)
