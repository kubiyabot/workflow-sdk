"""Base templates for creating tool_templates.

These templates provide the foundation for creating tool_templates that handle
authentication, environment setup, and common patterns.
"""

from typing import Dict, Any, List, Optional
from ...core import ToolDefinition


class ToolTemplate:
    """Base class for tool templates."""

    @staticmethod
    def create_base_tool(name: str, description: str, tool_type: str, **kwargs) -> ToolDefinition:
        """Create a base tool definition."""
        return ToolDefinition(name=name, description=description, type=tool_type, **kwargs)


class DockerToolTemplate:
    """Template for Docker-based tool_templates with common patterns."""

    @staticmethod
    def with_credentials(
        name: str,
        description: str,
        image: str,
        credential_files: List[Dict[str, str]],
        env_vars: List[str],
        **kwargs,
    ) -> ToolDefinition:
        """Create a Docker tool that mounts credentials and sets environment variables.

        Args:
            name: Tool name
            description: Tool description
            image: Docker image
            credential_files: List of files to mount (source, destination)
            env_vars: Environment variables to pass through
            **kwargs: Additional tool configuration

        Example:
            tool = DockerToolTemplate.with_credentials(
                name="aws_tool",
                description="AWS CLI tool",
                image="amazon/aws-cli:latest",
                credential_files=[
                    {"source": "$HOME/.aws/credentials", "destination": "/root/.aws/credentials"},
                    {"source": "$HOME/.aws/config", "destination": "/root/.aws/config"}
                ],
                env_vars=["AWS_PROFILE", "AWS_REGION"],
                content="aws s3 ls"
            )
        """
        return ToolDefinition(
            name=name,
            description=description,
            type="docker",
            image=image,
            env=env_vars,
            with_files=credential_files,
            **kwargs,
        )

    @staticmethod
    def with_workspace(
        name: str, description: str, image: str, workspace_path: str = "/workspace", **kwargs
    ) -> ToolDefinition:
        """Create a Docker tool that mounts the current workspace.

        Args:
            name: Tool name
            description: Tool description
            image: Docker image
            workspace_path: Path to mount workspace in container
            **kwargs: Additional tool configuration
        """
        return ToolDefinition(
            name=name,
            description=description,
            type="docker",
            image=image,
            with_volumes=[{"source": ".", "destination": workspace_path, "mode": "rw"}],
            **kwargs,
        )

    @staticmethod
    def with_startup_script(
        name: str, description: str, image: str, startup_script: str, main_content: str, **kwargs
    ) -> ToolDefinition:
        """Create a Docker tool with initialization/startup script.

        Args:
            name: Tool name
            description: Tool description
            image: Docker image
            startup_script: Script to run before main content
            main_content: Main script content
            **kwargs: Additional tool configuration

        Example:
            tool = DockerToolTemplate.with_startup_script(
                name="python_env_tool",
                description="Python tool with environment setup",
                image="python:3.11",
                startup_script='''
                    pip install -q pandas numpy
                    export PYTHONPATH=/app:$PYTHONPATH
                ''',
                main_content='''
                    import pandas as pd
                    # Your main logic here
                '''
            )
        """
        full_content = f"""#!/bin/bash
set -e

# Startup/initialization
{startup_script}

# Main execution
cat << 'EOF' | python
{main_content}
EOF
"""
        return ToolDefinition(
            name=name,
            description=description,
            type="docker",
            image=image,
            content=full_content,
            **kwargs,
        )


class AuthenticatedToolTemplate:
    """Templates for tool_templates that require authentication."""

    @staticmethod
    def oauth_tool(
        name: str,
        description: str,
        tool_type: str,
        oauth_provider: str,
        scopes: List[str],
        **kwargs,
    ) -> ToolDefinition:
        """Create a tool that uses OAuth authentication.

        Args:
            name: Tool name
            description: Tool description
            tool_type: Tool type (docker, python, etc.)
            oauth_provider: OAuth provider name (e.g., 'google', 'github')
            scopes: Required OAuth scopes
            **kwargs: Additional tool configuration
        """
        # Add OAuth metadata
        oauth_config = {"auth_type": "oauth", "provider": oauth_provider, "scopes": scopes}

        # Add OAuth token to env
        if "env" not in kwargs:
            kwargs["env"] = []
        kwargs["env"].append(f"{oauth_provider.upper()}_TOKEN")

        # Store auth config in args for now (since metadata field doesn't exist)
        if "args" not in kwargs:
            kwargs["args"] = []
        kwargs["args"].append(
            {"name": "_auth_metadata", "type": "object", "value": oauth_config, "hidden": True}
        )

        return ToolDefinition(name=name, description=description, type=tool_type, **kwargs)

    @staticmethod
    def api_key_tool(
        name: str,
        description: str,
        tool_type: str,
        api_key_env_var: str,
        api_base_url: Optional[str] = None,
        **kwargs,
    ) -> ToolDefinition:
        """Create a tool that uses API key authentication.

        Args:
            name: Tool name
            description: Tool description
            tool_type: Tool type
            api_key_env_var: Environment variable name for API key
            api_base_url: Optional API base URL
            **kwargs: Additional tool configuration
        """
        env_vars = [api_key_env_var]
        if api_base_url:
            env_vars.append(f"{api_key_env_var.replace('_KEY', '_URL')}")

        return ToolDefinition(
            name=name,
            description=description,
            type=tool_type,
            env=env_vars,
            secrets=[api_key_env_var],
            **kwargs,
        )

    @staticmethod
    def service_account_tool(
        name: str,
        description: str,
        tool_type: str,
        service_account_file: str,
        service_account_env_var: str,
        **kwargs,
    ) -> ToolDefinition:
        """Create a tool that uses service account authentication.

        Args:
            name: Tool name
            description: Tool description
            tool_type: Tool type
            service_account_file: Path to service account file
            service_account_env_var: Environment variable for service account
            **kwargs: Additional tool configuration
        """
        return ToolDefinition(
            name=name,
            description=description,
            type=tool_type,
            env=[service_account_env_var],
            with_files=[
                {
                    "source": service_account_file,
                    "destination": f"/tmp/{service_account_env_var.lower()}.json",
                }
            ],
            **kwargs,
        )


class CLIToolTemplate:
    """Templates for CLI-based tool_templates."""

    @staticmethod
    def cloud_cli(
        name: str,
        description: str,
        cli_name: str,  # aws, gcloud, az, etc.
        image: str,
        auth_method: str,  # credentials, service_account, etc.
        **kwargs,
    ) -> ToolDefinition:
        """Create a cloud CLI tool with proper authentication setup.

        Args:
            name: Tool name
            description: Tool description
            cli_name: CLI name (aws, gcloud, az)
            image: Docker image for the CLI
            auth_method: Authentication method
            **kwargs: Additional configuration
        """
        # Common patterns for cloud CLIs
        auth_configs = {
            "aws": {
                "credentials": {
                    "files": [
                        {
                            "source": "$HOME/.aws/credentials",
                            "destination": "/root/.aws/credentials",
                        },
                        {"source": "$HOME/.aws/config", "destination": "/root/.aws/config"},
                    ],
                    "env": ["AWS_PROFILE", "AWS_REGION", "AWS_DEFAULT_REGION"],
                },
                "iam_role": {"env": ["AWS_ROLE_ARN", "AWS_WEB_IDENTITY_TOKEN_FILE"]},
            },
            "gcloud": {
                "service_account": {
                    "files": [
                        {
                            "source": "$GOOGLE_APPLICATION_CREDENTIALS",
                            "destination": "/tmp/gcp-key.json",
                        }
                    ],
                    "env": [
                        "GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcp-key.json",
                        "GOOGLE_CLOUD_PROJECT",
                    ],
                },
                "oauth": {
                    "files": [
                        {"source": "$HOME/.config/gcloud", "destination": "/root/.config/gcloud"}
                    ],
                    "env": ["GOOGLE_CLOUD_PROJECT"],
                },
            },
            "az": {
                "service_principal": {
                    "env": [
                        "AZURE_CLIENT_ID",
                        "AZURE_CLIENT_SECRET",
                        "AZURE_TENANT_ID",
                        "AZURE_SUBSCRIPTION_ID",
                    ]
                },
                "managed_identity": {"env": ["AZURE_CLIENT_ID", "AZURE_SUBSCRIPTION_ID"]},
            },
        }

        # Get auth configuration
        cli_auth = auth_configs.get(cli_name, {}).get(auth_method, {})

        return ToolDefinition(
            name=name,
            description=description,
            type="docker",
            image=image,
            env=cli_auth.get("env", []),
            with_files=cli_auth.get("files", []),
            **kwargs,
        )

    @staticmethod
    def kubernetes_tool(
        name: str,
        description: str,
        image: str = "bitnami/kubectl:latest",
        kubeconfig_source: str = "$HOME/.kube/config",
        namespace: Optional[str] = None,
        **kwargs,
    ) -> ToolDefinition:
        """Create a Kubernetes CLI tool.

        Args:
            name: Tool name
            description: Tool description
            image: Docker image with kubectl
            kubeconfig_source: Path to kubeconfig
            namespace: Default namespace
            **kwargs: Additional configuration
        """
        env_vars = ["KUBECONFIG=/root/.kube/config"]
        if namespace:
            env_vars.append(f"KUBECTL_NAMESPACE={namespace}")

        return ToolDefinition(
            name=name,
            description=description,
            type="docker",
            image=image,
            env=env_vars,
            with_files=[{"source": kubeconfig_source, "destination": "/root/.kube/config"}],
            **kwargs,
        )


class DataProcessingToolTemplate:
    """Templates for data processing tool_templates."""

    @staticmethod
    def with_data_volumes(
        name: str,
        description: str,
        image: str,
        input_path: str,
        output_path: str,
        processing_script: str,
        **kwargs,
    ) -> ToolDefinition:
        """Create a data processing tool with input/output volumes.

        Args:
            name: Tool name
            description: Tool description
            image: Docker image
            input_path: Input data path
            output_path: Output data path
            processing_script: Data processing script
            **kwargs: Additional configuration
        """
        return ToolDefinition(
            name=name,
            description=description,
            type="docker",
            image=image,
            content=processing_script,
            with_volumes=[
                {"source": input_path, "destination": "/data/input", "mode": "ro"},
                {"source": output_path, "destination": "/data/output", "mode": "rw"},
            ],
            **kwargs,
        )

    @staticmethod
    def streaming_processor(
        name: str,
        description: str,
        image: str,
        process_function: str,
        buffer_size: int = 1024,
        **kwargs,
    ) -> ToolDefinition:
        """Create a streaming data processor tool.

        Args:
            name: Tool name
            description: Tool description
            image: Docker image
            process_function: Function to process each data item
            buffer_size: Buffer size for streaming
            **kwargs: Additional configuration
        """
        streaming_wrapper = f"""
import sys
import json

def process_stream(buffer_size={buffer_size}):
    buffer = []
    
    {process_function}
    
    for line in sys.stdin:
        item = json.loads(line.strip())
        result = process_item(item)
        
        buffer.append(result)
        if len(buffer) >= buffer_size:
            for item in buffer:
                print(json.dumps(item))
            buffer = []
    
    # Flush remaining items
    for item in buffer:
        print(json.dumps(item))

if __name__ == "__main__":
    process_stream()
"""

        return ToolDefinition(
            name=name,
            description=description,
            type="docker",
            image=image,
            content=streaming_wrapper,
            **kwargs,
        )


# Export template classes
__all__ = [
    "ToolTemplate",
    "DockerToolTemplate",
    "AuthenticatedToolTemplate",
    "CLIToolTemplate",
    "DataProcessingToolTemplate",
]
