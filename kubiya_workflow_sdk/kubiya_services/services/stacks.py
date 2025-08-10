"""
Stacks service for managing Terraform stacks
"""
import base64
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Union, Generator
from pydantic import BaseModel, Field, field_validator, model_validator

from kubiya_workflow_sdk.kubiya_services.services.base import BaseService
from kubiya_workflow_sdk.kubiya_services.constants import Endpoints
from kubiya_workflow_sdk.kubiya_services.exceptions import StackError, StackPlanError, StackApplyError, StackStreamError

from kubiya_workflow_sdk import capture_exception

logger = logging.getLogger(__name__)


class StackFiles(BaseModel):
    """Terraform files for stack deployment
    
    Accepts either file content directly or file paths.
    If file paths are provided, content will be read from those files.
    """
    main_tf: Optional[str] = Field(None, description="Main Terraform configuration content")
    variables_tf: Optional[str] = Field(None, description="Terraform variables configuration content")
    main_tf_path: Optional[Union[str, Path]] = Field(None, description="Path to main.tf file")
    variables_tf_path: Optional[Union[str, Path]] = Field(None, description="Path to variables.tf file")

    @model_validator(mode='after')
    def validate_files(self):
        """Ensure either content or path is provided for each file"""
        if not self.main_tf and not self.main_tf_path:
            raise ValueError("Either main_tf content or main_tf_path must be provided")
        if not self.variables_tf and not self.variables_tf_path:
            raise ValueError("Either variables_tf content or variables_tf_path must be provided")
        return self

    def get_main_tf_content(self) -> str:
        """Get main.tf content, reading from file if path is provided"""
        if self.main_tf:
            return self.main_tf
        elif self.main_tf_path:
            path = Path(self.main_tf_path)
            if not path.exists():
                raise FileNotFoundError(f"Main terraform file not found: {path}")
            return path.read_text(encoding='utf-8')
        else:
            raise ValueError("No main_tf content or path provided")

    def get_variables_tf_content(self) -> str:
        """Get variables.tf content, reading from file if path is provided"""
        if self.variables_tf:
            return self.variables_tf
        elif self.variables_tf_path:
            path = Path(self.variables_tf_path)
            if not path.exists():
                raise FileNotFoundError(f"Variables terraform file not found: {path}")
            return path.read_text(encoding='utf-8')
        else:
            raise ValueError("No variables_tf content or path provided")


class StackRequest(BaseModel):
    """Request model for stack operations"""
    name: str = Field(..., description="Name of the Terraform stack")
    files: StackFiles = Field(..., description="Terraform configuration files")

    def to_api_dict(self) -> Dict[str, Any]:
        """Convert to API request format with base64 encoded file content"""
        # Get file contents
        main_tf_content = self.files.get_main_tf_content()
        variables_tf_content = self.files.get_variables_tf_content()
        
        # Base64 encode the file contents
        main_tf_b64 = base64.b64encode(main_tf_content.encode('utf-8')).decode('ascii')
        variables_tf_b64 = base64.b64encode(variables_tf_content.encode('utf-8')).decode('ascii')
        
        return {
            "name": self.name,
            "files": {
                "main.tf": main_tf_b64,
                "variables.tf": variables_tf_b64
            }
        }


class StacksService(BaseService):
    """Service for managing Terraform stacks"""
    
    def __init__(self, client):
        """Initialize StacksService with client and internal state tracking"""
        super().__init__(client)
        self._current_stack_id: Optional[str] = None
        self._current_stack_name: Optional[str] = None

    def plan(self, stack_request: StackRequest) -> Dict[str, Any]:
        """
        Plan a Terraform stack deployment

        Args:
            stack_request: Stack configuration with name and files

        Returns:
            Dictionary containing plan response data

        Raises:
            StackPlanError: For planning-specific errors
        """
        try:
            endpoint = self._format_endpoint(Endpoints.STACKS_PLAN)
            request_data = stack_request.to_api_dict()
            
            response = self._post(endpoint=endpoint, data=request_data, stream=False)
            
            if hasattr(response, 'json'):
                try:
                    result = response.json()
                    
                    # Check for plan failure in response
                    if result.get("success") is False or "errorMessage" in result:
                        error_message = result.get("errorMessage", "Unknown plan error")
                        
                        # Extract terraform-specific errors for better context
                        terraform_errors = {
                            "errorMessage": error_message,
                            "initOutput": result.get("initOutput"),
                            "planOutput": result.get("planOutput")
                        }
                        
                        error = StackPlanError(
                            f"Stack plan failed for '{stack_request.name}': {error_message}",
                            stack_name=stack_request.name,
                            validation_errors=terraform_errors
                        )
                        capture_exception(error)
                        raise error
                    return result
                except StackPlanError:
                    raise  # Re-raise StackPlanError as-is
                except Exception as json_error:
                    error = StackPlanError(
                        f"Failed to parse plan response for stack '{stack_request.name}': {str(json_error)}",
                        stack_name=stack_request.name
                    )
                    capture_exception(error)
                    raise error
            else:
                return response

        except StackPlanError:
            raise
        except Exception as e:
            error = StackPlanError(
                f"Failed to plan stack '{stack_request.name}': {str(e)}",
                stack_name=stack_request.name
            )
            capture_exception(error)
            raise error

    def apply(self, stack_request: StackRequest) -> Dict[str, Any]:
        """
        Apply a Terraform stack deployment

        Args:
            stack_request: Stack configuration with name and files

        Returns:
            Dictionary containing apply response data with task_id for streaming

        Raises:
            StackApplyError: For apply-specific errors
        """
        try:
            endpoint = self._format_endpoint(Endpoints.STACKS_APPLY)
            request_data = stack_request.to_api_dict()
            
            response = self._post(endpoint=endpoint, data=request_data, stream=False)
            
            if hasattr(response, 'json'):
                try:
                    result = response.json()
                    
                    # Check for apply failure in response  
                    if result.get("success") is False or "errorMessage" in result or result.get("error") is not None:
                        error_message = result.get("errorMessage", "unknown apply error")

                        # Extract terraform-specific errors for better context
                        terraform_errors = {
                            "errorMessage": error_message,
                            "result": result,
                        }
                        
                        error = StackApplyError(
                            f"Stack apply failed for '{stack_request.name}': {error_message}",
                            stack_name=stack_request.name,
                            stack_id=result.get("uuid"),
                            terraform_errors=terraform_errors
                        )
                        capture_exception(error)
                        raise error
                    
                    # Store the stack ID and name for later streaming
                    self._current_stack_id = result.get("uuid")
                    self._current_stack_name = stack_request.name
                    
                    return result
                except StackApplyError:
                    raise  # Re-raise StackApplyError as-is
                except Exception as json_error:
                    error = StackApplyError(
                        f"Failed to parse apply response for stack '{stack_request.name}': {str(json_error)}",
                        stack_name=stack_request.name
                    )
                    capture_exception(error)
                    raise error
            else:
                return response

        except StackApplyError:
            raise
        except Exception as e:
            error = StackApplyError(
                f"Failed to apply stack '{stack_request.name}': {str(e)}",
                stack_name=stack_request.name
            )
            capture_exception(error)
            raise error

    def stream(self, stack_id: Optional[str] = None) -> Generator[str, None, None]:
        """
        Stream logs from a Terraform stack apply operation

        Args:
            stack_id: Optional stack ID. If not provided, uses the stack ID from the last apply operation

        Returns:
            Generator yielding log data

        Raises:
            StackStreamError: For streaming-specific errors
        """
        # Use provided stack_id or fall back to internal state
        current_stack_id = stack_id or self._current_stack_id
        
        if not current_stack_id:
            error = StackStreamError(
                "Stack ID is required for streaming logs. Either provide stack_id parameter or call apply() first."
            )
            capture_exception(error)
            raise error

        try:
            endpoint = self._format_endpoint(Endpoints.STACKS_STREAM, stack_id=current_stack_id)

            # Use BaseService stream method to get raw response for SSE streaming  
            response = self._stream_request(method="GET", endpoint=endpoint)

            for line in response:
                yield line

        except StackStreamError:
            raise
        except Exception as e:
            # Use the effective stack name for error context
            stack_name = self._current_stack_name if current_stack_id == self._current_stack_id else current_stack_id
            error = StackStreamError(
                f"Failed to stream logs for stack '{stack_name}': {str(e)}",
                stack_id=current_stack_id
            )
            capture_exception(error)
            raise error