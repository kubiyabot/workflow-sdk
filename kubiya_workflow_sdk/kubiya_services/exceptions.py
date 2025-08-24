from typing import Optional, Dict, Any


class KubiyaSDKError(Exception):
    """Base exception for all Kubiya SDK errors"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} - Details: {self.details}"
        return self.message

class WorkflowError(KubiyaSDKError):
    """Exception for workflow-related errors"""

    def __init__(self, message: str, workflow_id: Optional[str] = None, execution_id: Optional[str] = None):
        details = {}
        if workflow_id:
            details["workflow_id"] = workflow_id
        if execution_id:
            details["execution_id"] = execution_id
        super().__init__(message, details)

class WorkflowExecutionError(WorkflowError):
    """Exception for workflow execution errors"""

    def __init__(
            self,
            message: str,
            workflow_id: Optional[str] = None,
            execution_id: Optional[str] = None,
            step: Optional[str] = None
    ):
        super().__init__(message, workflow_id, execution_id)
        if step:
            self.details["step"] = step


class PaginationError(KubiyaSDKError):
    """Exception for pagination-related errors"""

    def __init__(self, message: str, page: Optional[int] = None, limit: Optional[int] = None):
        details = {}
        if page is not None:
            details["page"] = page
        if limit is not None:
            details["limit"] = limit
        super().__init__(message, details)


class ValidationError(KubiyaSDKError):
    """Exception for validation errors"""

    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None):
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = value
        super().__init__(message, details)


class KubiyaAPIError(KubiyaSDKError):
    """Exception for API-related errors"""

    def __init__(
            self,
            message: str,
            status_code: Optional[int] = None,
            response: Optional[Dict[str, Any]] = None,
            request_id: Optional[str] = None
    ):
        super().__init__(message, response)
        self.status_code = status_code
        self.response = response or {}
        self.request_id = request_id

    def __str__(self) -> str:
        parts = [self.message]
        if self.status_code:
            parts.append(f"Status: {self.status_code}")
        if self.request_id:
            parts.append(f"Request ID: {self.request_id}")
        if self.response:
            parts.append(f"Response: {self.response}")
        return " | ".join(parts)


class NotFoundError(KubiyaAPIError):
    """Exception for resource not found errors"""

    def __init__(self, resource_type: str, resource_id: str):
        message = f"{resource_type} with ID '{resource_id}' not found"
        super().__init__(message, status_code=404)
        self.resource_type = resource_type
        self.resource_id = resource_id


class WebhookError(KubiyaSDKError):
    """Exception for webhook-related errors"""

    def __init__(self, message: str, webhook_id: Optional[str] = None):
        details = {"webhook_id": webhook_id} if webhook_id else None
        super().__init__(message, details)

class StackError(KubiyaSDKError):
    """Exception for stack-related errors"""

    def __init__(self, message: str, stack_name: Optional[str] = None, stack_id: Optional[str] = None):
        details = {}
        if stack_name:
            details["stack_name"] = stack_name
        if stack_id:
            details["stack_id"] = stack_id
        super().__init__(message, details)


class StackPlanError(StackError):
    """Exception for stack planning errors"""

    def __init__(
        self,
        message: str,
        stack_name: Optional[str] = None,
        validation_errors: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, stack_name)
        if validation_errors:
            self.details["validation_errors"] = validation_errors


class StackApplyError(StackError):
    """Exception for stack apply errors"""

    def __init__(
        self,
        message: str,
        stack_name: Optional[str] = None,
        stack_id: Optional[str] = None,
        terraform_errors: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, stack_name, stack_id)
        if terraform_errors:
            self.details["terraform_errors"] = terraform_errors


class StackStreamError(StackError):
    """Exception for stack streaming errors"""

    def __init__(
        self,
        message: str,
        stack_id: Optional[str] = None,
        stream_position: Optional[int] = None
    ):
        super().__init__(message, stack_id=stack_id)
        if stream_position is not None:
            self.details["stream_position"] = stream_position



class AuthorizationError(KubiyaSDKError):
    """Exception for authorization-related errors"""

    def __init__(self, message: str = "Access denied", resource: Optional[str] = None):
        details = {"resource": resource} if resource else None
        super().__init__(message, details)


# User service exceptions
class UserError(Exception):
    """Base exception for user service operations"""
    pass

class UserNotFoundError(UserError):
    """Exception raised when a user is not found"""
    pass

class GroupError(Exception):
    """Base exception for group service operations"""
    pass

class GroupNotFoundError(GroupError):
    """Exception raised when a group is not found"""
    pass


# Trigger service exceptions
class TriggerError(Exception):
    """Trigger-related error"""
    pass

class TriggerValidationError(Exception):
    """Trigger validation error"""
    pass

class ProviderError(Exception):
    """Provider-specific error"""
    pass


# Tool service exceptions
class ToolError(Exception):
    """Base exception for tool service operations"""
    pass


class ToolNotFoundError(ToolError):
    """Exception raised when a tool is not found"""
    pass


class ToolExecutionError(ToolError):
    """Exception raised when tool execution fails"""
    pass

class ToolGenerationError(ToolError):
    """Tool generation errors"""
    pass


class SourceError(KubiyaSDKError):
    """Exception for source-related errors"""

    def __init__(self, message: str, source_id: Optional[str] = None, source_type: Optional[str] = None):
        details = {}
        if source_id:
            details["source_id"] = source_id
        if source_type:
            details["source_type"] = source_type
        super().__init__(message, details)

class SourceNotFoundError(SourceError):
    """Exception raised when a source is not found"""
    pass

class SourceValidationError(SourceError):
    """Exception raised when source validation fails"""
    pass


class SecretError(KubiyaSDKError):
    """Exception for secret-related errors"""

    def __init__(self, message: str, secret_name: Optional[str] = None):
        details = {"secret_name": secret_name} if secret_name else None
        super().__init__(message, details)


class SecretValidationError(SecretError):
    """Exception raised when secret validation fails"""
    pass

class RunnerError(KubiyaSDKError):
    """Runner-related errors"""
    pass

class RunnerNotFoundError(RunnerError):
    """Runner not found errors"""
    pass

class RunnerHealthError(RunnerError):
    """Runner health check errors"""
    pass

class ProjectExecutionError(KubiyaSDKError):
    """Project execution errors"""
    pass

# Policy-specific exceptions
class PolicyError(KubiyaSDKError):
    """Policy-related errors"""
    pass

class PolicyValidationError(ValidationError):
    """Policy validation errors"""
    pass

class PolicyDeniedError(AuthorizationError):
    """Policy denied errors"""
    pass


class KnowledgeError(KubiyaSDKError):
    """Exception for knowledge-related errors"""

    def __init__(self, message: str, knowledge_id: Optional[str] = None):
        details = {"knowledge_id": knowledge_id} if knowledge_id else None
        super().__init__(message, details)


# Integration-specific exceptions
class IntegrationError(KubiyaSDKError):
    """Integration-related errors"""
    pass

class IntegrationNotFoundError(IntegrationError):
    """Integration not found errors"""
    pass

class IntegrationValidationError(ValidationError):
    """Integration validation errors"""
    pass

class ProjectValidationError(ValidationError):
    """Project validation errors"""
    pass

# Documentation-specific exceptions
class DocumentationError(KubiyaSDKError):
    """Documentation-related errors"""
    pass

# Audit-specific exceptions
class AuditError(KubiyaSDKError):
    """Audit-related errors"""
    pass

# Agent-specific exceptions
class AgentError(KubiyaSDKError):
    """Agent-related errors"""
    pass

class AgentNotFoundError(NotFoundError):
    """Agent not found errors"""
    pass

class AgentValidationError(ValidationError):
    """Agent validation errors"""
    pass
