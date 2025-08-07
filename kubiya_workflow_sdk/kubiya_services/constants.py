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

    # Users endpoints
    USER_LIST = "/api/v2/users"

    # Groups endpoints
    GROUP_LIST = "/api/v1/manage/groups"

    # Tool endpoints
    TOOL_EXECUTE = "/api/v1/tools/exec?runner={runner}"
    TOOL_GENERATE = "/api/v2/tools/generate"
    TOOL_LIST = "/tools"
    TOOL_DESCRIBE = "/tools/{tool_name}"
    TOOL_SEARCH = "/tools/search"

    # Source endpoints - for listing tools from sources
    SOURCES_LIST = "/api/v1/sources"
    SOURCE_GET = "/api/v1/sources/{source_uuid}"
    SOURCE_METADATA = "/api/v1/sources/{source_uuid}/metadata"
    SOURCE_DELETE = "/api/v1/sources/{source_uuid}"
    SOURCE_LOAD = "/api/v1/sources/load"
    SOURCE_ZIP = "/api/v1/sources/zip"
    SOURCE_ZIP_LOAD = "/api/v1/sources/zip/load"

    # Runner endpoints - for tool execution
    RUNNERS_LIST = "/api/v3/runners"
    RUNNER_GET = "/api/v3/runners/{runner_name}"
    RUNNER_HELM_CHART = "/api/v3/runners/helmchart/{runner_name}"
    RUNNER_MANIFEST = "/api/v3/runners/{runner_name}"
    RUNNER_HEALTH = "/api/v3/runners/{runner_name}/health"
