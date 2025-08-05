class Endpoints:
    """API endpoint constants"""

    # Workflow endpoints
    WORKFLOW_EXECUTE = "/api/v1/workflow?runner={runner}&operation=execute_workflow"
    WORKFLOW_LIST = "/api/v1/workflow?runner={runner}&operation=list_workflows"
    WORKFLOW_STATUS = "/api/v1/workflow?runner={runner}&operation=get_status"

    # Webhook endpoints
    WEBHOOK_LIST = "/api/v1/event"
    WEBHOOK_GET = "/api/v1/event/{webhook_id}"
    WEBHOOK_CREATE = "/api/v1/event"
    WEBHOOK_UPDATE = "/api/v1/event/{webhook_id}"
    WEBHOOK_DELETE = "/api/v1/event/{webhook_id}"
    WEBHOOK_TEST = "/api/v1/webhook/test"


# Pagination Constants
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100