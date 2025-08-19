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
    TOOL_GENERATE = "/api/v1/http-bridge/v1/generate-tool"
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
    SOURCE_SYNC = "/api/v1/sources/{source_uuid}/sync"

    # Runner endpoints - for tool execution
    RUNNERS_LIST = "/api/v3/runners"
    RUNNERS_DESCRIBE = "/api/v1/runners/{runner_name}/describe"
    RUNNER_GET = "/api/v3/runners/{runner_name}"
    RUNNER_HELM_CHART = "/api/v3/runners/helmchart/{runner_name}"
    RUNNER_MANIFEST = "/api/v3/runners/{runner_name}"
    RUNNER_HEALTH = "/api/v3/runners/{runner_name}/health"

    # Secrets endpoints
    SECRETS_CREATE = "/api/v1/secrets"
    SECRETS_LIST = "/api/v1/secrets"
    SECRETS_GET = "/api/v1/secrets/{secret_name}"
    SECRETS_GET_VALUE = "/api/v1/secrets/get_value/{secret_name}"
    SECRETS_UPDATE = "/api/v1/secrets/{secret_name}"
    SECRETS_DELETE = "/api/v1/secrets/{secret_name}"

    # Project endpoints (tasks and usecases)
    PROJECT_LIST = "/api/v1/usecases"
    PROJECT_GET = "/api/v1/tasks/{project_id}"
    PROJECT_CREATE = "/api/v1/usecases"
    PROJECT_UPDATE = "/api/v1/tasks/{project_id}"
    PROJECT_DELETE = "/api/v1/tasks/{project_id}"
    PROJECT_TEMPLATES_LIST = "/api/v1/usecases"
    PROJECT_TEMPLATE_GET = "/api/v1/usecases/{template_id}"
    PROJECT_PLAN_CREATE = "/api/v1/tasks/plan/{project_id}"
    PROJECT_PLAN_GET = "/api/v1/tasks/plan/{plan_id}"
    PROJECT_PLAN_APPROVE = "/api/v1/tasks/{plan_id}"
    PROJECT_EXECUTION_GET = "/api/v1/tasks/{execution_id}"
    PROJECT_EXECUTION_LOGS = "/api/v1/tasks/logs/{execution_id}"

    # Policy endpoints - for OPA policy management
    POLICY_LIST = "/api/v1/opa/policies"
    POLICY_GET = "/api/v1/opa/policies/{policy_name}"
    POLICY_CREATE = "/api/v1/opa/policies"
    POLICY_UPDATE = "/api/v1/opa/policies/{policy_name}"
    POLICY_DELETE = "/api/v1/opa/policies/{policy_name}"
    POLICY_VALIDATE = "/api/v1/opa/policies/validate"
    POLICY_EVALUATE = "/api/v1/opa/policies/evaluate"

    # Knowledge endpoints
    KNOWLEDGE_QUERY = "/api/query"
    KNOWLEDGE_LIST = "/knowledge"
    KNOWLEDGE_GET = "/knowledge/{knowledge_id}"

    # Integration endpoints
    INTEGRATIONS_LIST = "/api/v1/integrations"
    INTEGRATION_GET = "/api/v1/integrations/{integration_name}"
    INTEGRATIONS_GITHUB = "/api/v2/integrations/github_app"
    INTEGRATION_INSTALL = "/api/v1/integration/{integration_name}/install"

    # Documentation endpoints
    DOCUMENTATION_LIST = "/documentation"
    DOCUMENTATION_GET = "/documentation/{doc_id}"

    # Audit endpoints
    AUDIT_LIST = "/api/v1/auditing/items"
    AUDIT_GET = "/api/v1/auditing/items/{audit_id}"
    AUDIT_STREAM = "/api/v1/auditing/items/stream"

    # Agent endpoints
    AGENTS_LIST = "/api/v1/agents"
    AGENT_GET = "/api/v1/agents/{agent_uuid}"
    AGENT_CREATE = "/api/v1/agents"
    AGENT_UPDATE = "/api/v1/agents/{agent_uuid}"
    AGENT_DELETE = "/api/v1/agents/{agent_uuid}"

    # Stacks endpoints
    STACKS_PLAN = "api/v1/tasks/inline/plan"
    STACKS_APPLY = "/api/v1/tasks/inline"
    STACKS_STREAM = "/api/v1/tasks/stream/logs/{stack_id}"