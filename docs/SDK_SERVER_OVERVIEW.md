# SDK Server Overview

## Summary

FastAPI-based REST server for the Kubiya Workflow SDK with basic workflow execution capabilities.

## Key Components Implemented

### 1. **SDK Server** (`kubiya_workflow_sdk/server/`)

A FastAPI-based REST API server that provides:

- **REST Endpoints**:
  - `GET /health` - Health check endpoint
  - `GET /api/v1/providers` - List available AI providers
  - `POST /api/v1/compose` - Generate/execute workflows with AI
  - `POST /api/v1/workflows/execute` - Direct workflow execution

- **Features**:
  - SSE (Server-Sent Events) streaming for real-time updates
  - Authentication via Bearer tokens
  - CORS support for web applications
  - OpenAPI/Swagger documentation
  - Async request handling

### 2. **ADK Provider** (`kubiya_workflow_sdk/providers/adk/`)

First-class AI provider implementation using Google's Agent Development Kit:

- **Architecture**:
  - Modular agent system with specialized agents
  - Uses DeepSeek V3 models via Together AI (default)
  - Support for Google AI and Vertex AI models
  - Session-based context management

- **Agents**:
  - **ContextLoaderAgent**: Loads platform resources (runners, integrations, secrets)
  - **WorkflowGeneratorAgent**: Generates workflow code from natural language
  - **CompilerAgent**: Validates Python syntax
  - **WorkflowValidatorAgent**: Validates against requirements
  - **RefinementAgent**: Fixes errors using advanced reasoning
  - **WorkflowExecutorAgent**: Executes workflows with SSE streaming
  - **LoopOrchestratorAgent**: Coordinates the entire process

- **Modes**:
  - **Plan Mode**: Generate workflows without execution
  - **Act Mode**: Generate and immediately execute workflows

- **Streaming Formats**:
  - Standard SSE format
  - Vercel AI SDK format
  - Raw ADK events

### 3. **Enhanced SDK Client** (`kubiya_workflow_sdk/client.py`)

Extended with new capabilities:

- **New Methods**:
  - `get_runners()` - List available execution environments
  - `get_integrations()` - List platform integrations
  - `get_secrets_metadata()` - List available secrets
  - `get_organization_info()` - Get org details
  - `create_agent()` - Create platform agents
  - `execute_agent()` - Execute platform agents

- **Fixes**:
  - Correct API endpoint format (`operation=execute_workflow`)
  - Native SSE streaming support (`native_sse=true`)
  - Proper Kubiya event format parsing
  - Python 3.9 compatibility

### 4. **Documentation** (`docs/`)

Comprehensive documentation using Mintlify format:

- **Structure**:
  ```
  docs/kubiya/
  ├── getting-started/
  │   ├── welcome.mdx
  │   ├── installation.mdx
  │   ├── quickstart.mdx
  │   └── concepts.mdx
  ├── providers/
  │   └── adk/
  │       ├── getting-started.mdx
  │       ├── configuration.mdx
  │       └── examples.mdx
  ├── servers/
  ├── workflows/
  └── deployment/
  ```

- **Interactive Examples**:
  - Jupyter notebooks in `examples/notebooks/`
  - Getting started notebook
  - AI workflow generation notebook

### 5. **Deployment** 

Production-ready deployment configurations:

- **Docker**:
  - Multi-stage Dockerfile for optimized builds
  - Health checks and non-root user
  - Startup script with environment validation

- **Docker Compose**:
  - Main SDK server
  - Optional Redis for caching
  - Optional PostgreSQL for history
  - Nginx reverse proxy
  - Prometheus/Grafana monitoring

- **Kubernetes**:
  - Deployment manifests
  - Service definitions
  - ConfigMaps and Secrets

### 6. **Development Tools**

- **Makefile**: Common development commands
- **Environment Configuration**: `env.example` with all options
- **Testing**: End-to-end test suite (`test_server_e2e.py`)

## API Usage Examples

### Generate Workflow (Plan Mode)

```bash
curl -X POST http://localhost:8000/api/v1/compose \
  -H "Authorization: Bearer $KUBIYA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "adk",
    "task": "Create a workflow to backup databases to S3",
    "mode": "plan"
  }'
```

### Generate and Execute (Act Mode)

```bash
curl -X POST http://localhost:8000/api/v1/compose \
  -H "Authorization: Bearer $KUBIYA_API_KEY" \
  -H "Accept: text/event-stream" \
  -d '{
    "provider": "adk",
    "task": "Check system health and alert on issues",
    "mode": "act",
    "stream": true
  }'
```

### Python Client Usage

```python
from kubiya_workflow_sdk.providers import get_provider

# Initialize ADK provider
adk = get_provider("adk")

# Generate and execute workflow
async for event in adk.compose(
    task="Deploy my application with health checks",
    mode="act",
    stream=True
):
    print(event)
```

## Configuration

### Required Environment Variables

```bash
# Kubiya Platform
export KUBIYA_API_KEY="your-kubiya-api-key"

# AI Provider (for ADK)
export TOGETHER_API_KEY="your-together-api-key"
```

### Optional Configuration

```python
from kubiya_workflow_sdk.providers.adk import ADKProviderConfig

config = ADKProviderConfig(
    model_provider="together",  # or "google", "vertex"
    execute_workflows=True,
    max_loop_iterations=3,
    stream_format="sse"
)
```

## Key Features

1. **Natural Language to Workflow**: Describe tasks in plain English
2. **Automatic Error Correction**: AI fixes syntax and logic errors
3. **Real-time Streaming**: Watch workflows generate and execute
4. **Platform Integration**: Full access to Kubiya platform resources
5. **Extensible**: Easy to add new AI providers
6. **Production Ready**: Docker, monitoring, logging, error handling

## Architecture Benefits

- **Modular Design**: Each component has a single responsibility
- **Async Throughout**: Non-blocking I/O for performance
- **Type Safe**: Full type hints for better IDE support
- **Well Tested**: Comprehensive test coverage
- **Documented**: Extensive documentation and examples

## Next Steps

1. **Deploy the Server**: Use Docker Compose for quick start
2. **Try the Examples**: Run the Jupyter notebooks
3. **Generate Workflows**: Use natural language to create automations
4. **Extend**: Add custom providers or integrate with your tools

The implementation provides a solid foundation for AI-powered workflow automation that bridges the gap between natural language descriptions and production-ready workflows. 