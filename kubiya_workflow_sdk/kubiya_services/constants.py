class Endpoints:
    """API endpoint constants"""

    # Workflow endpoints
    WORKFLOW_EXECUTE = "/api/v1/workflow?runner={runner}&operation=execute_workflow"
    WORKFLOW_LIST = "/api/v1/workflow?runner={runner}&operation=list_workflows"
    WORKFLOW_STATUS = "/api/v1/workflow?runner={runner}&operation=get_status"


# Pagination Constants
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100