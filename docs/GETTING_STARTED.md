# Getting Started with Kubiya Workflow SDK

This guide will help you get up and running with the Kubiya Workflow SDK, including installation, configuration, and your first workflow.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Quick Start](#quick-start)
5. [Using the Server](#using-the-server)
6. [AI-Powered Workflows](#ai-powered-workflows)
7. [Docker Deployment](#docker-deployment)
8. [Next Steps](#next-steps)

## Prerequisites

- Python 3.9 or higher
- Kubiya API key ([Get one here](https://compose.kubiya.ai))
- (Optional) Together AI API key for ADK provider

## Installation

### From PyPI

```bash
pip install kubiya-workflow-sdk
```

### From Source

```bash
git clone https://github.com/kubiyabot/workflow_sdk.git
cd workflow-sdk
pip install -e .
```

## Configuration

### Environment Variables

Create a `.env` file or export these variables:

```bash
# Required
export KUBIYA_API_KEY="your-kubiya-api-key"

# Optional (for ADK provider)
export TOGETHER_API_KEY="your-together-api-key"

# Optional (override defaults)
export KUBIYA_API_URL="https://api.kubiya.ai/api/v1"
export KUBIYA_ORG_NAME="your-org-name"
```

## Quick Start

### 1. Basic Workflow Creation

```python
from kubiya_workflow_sdk import Workflow, Step, Client

# Define a workflow
workflow = Workflow(
    name="hello-world",
    description="My first workflow",
    steps=[
        Step(
            name="greeting",
            command="echo 'Hello from Kubiya!'",
            output="GREETING"
        ),
        Step(
            name="show_date",
            command="date",
            output="CURRENT_DATE"
        ),
        Step(
            name="final_message",
            command="echo 'Greeting: ${GREETING}, Date: ${CURRENT_DATE}'",
            depends=["greeting", "show_date"]
        )
    ]
)

# Execute the workflow
client = Client()
execution = client.execute_workflow(workflow)
print(f"Execution ID: {execution.id}")
```

### 2. Streaming Execution

```python
# Execute with real-time streaming
for event in client.execute_workflow(workflow, stream=True):
    if event.type == "step_started":
        print(f"Starting step: {event.step_name}")
    elif event.type == "step_completed":
        print(f"Completed step: {event.step_name}")
        print(f"Output: {event.output}")
    elif event.type == "workflow_completed":
        print(f"Workflow completed! Status: {event.status}")
```

### 3. Working with Integrations

```python
# List available integrations
integrations = client.get_integrations()
print("Available integrations:", [i.name for i in integrations])

# Use Slack integration
workflow = Workflow(
    name="slack-notification",
    description="Send Slack notification",
    integration="slack",
    steps=[
        Step(
            name="send_message",
            command="send_message",
            args={
                "channel": "#general",
                "text": "Workflow completed successfully!"
            }
        )
    ]
)
```

## Using the Server

The SDK includes a REST API server for remote access and AI-powered workflow generation.

### Starting the Server

```bash
# Start with default settings
kubiya-server

# Or with custom settings
kubiya-server --host 0.0.0.0 --port 8000 --reload
```

### API Endpoints

#### Health Check

```bash
curl http://localhost:8000/health
```

#### List Providers

```bash
curl http://localhost:8000/api/v1/providers
```

#### Generate Workflow (Plan Mode)

```bash
curl -X POST http://localhost:8000/api/v1/compose \
  -H "Authorization: Bearer $KUBIYA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "adk",
    "task": "Create a workflow that backs up a database and uploads to S3",
    "mode": "plan"
  }'
```

#### Generate and Execute (Act Mode)

```bash
curl -X POST http://localhost:8000/api/v1/compose \
  -H "Authorization: Bearer $KUBIYA_API_KEY" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "provider": "adk",
    "task": "List all Python files in the current directory and count lines of code",
    "mode": "act",
    "stream": true
  }'
```

## AI-Powered Workflows

The ADK provider enables natural language workflow generation:

### Python Example

```python
from kubiya_workflow_sdk.providers import get_provider

# Get the ADK provider
adk = get_provider("adk")

# Generate a workflow from natural language
result = await adk.compose(
    task="Create a workflow that monitors CPU usage and sends alerts if above 80%",
    mode="plan"
)

print(f"Generated workflow: {result['workflow'].name}")
print(f"Steps: {len(result['workflow'].steps)}")
```

### Using with Streaming

```python
# Generate and execute with streaming
async for event in adk.compose(
    task="Deploy a web application with health checks",
    mode="act",
    stream=True
):
    if event.get("type") == "text":
        print(event.get("content"))
    elif event.get("type") == "execution":
        print(f"Execution: {event.get('data')}")
```

## Docker Deployment

### Build the Image

```bash
docker build -t kubiya-sdk-server .
```

### Run the Container

```bash
docker run -d \
  --name kubiya-server \
  -p 8000:8000 \
  -e KUBIYA_API_KEY=$KUBIYA_API_KEY \
  -e TOGETHER_API_KEY=$TOGETHER_API_KEY \
  kubiya-sdk-server
```

### Docker Compose

```yaml
version: '3.8'

services:
  kubiya-server:
    image: kubiya-sdk-server
    ports:
      - "8000:8000"
    environment:
      - KUBIYA_API_KEY=${KUBIYA_API_KEY}
      - TOGETHER_API_KEY=${TOGETHER_API_KEY}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## Next Steps

1. **Explore Examples**: Check out the `examples/` directory
2. **Read the API Docs**: Visit `/docs` when running the server
3. **Create Custom Providers**: See [Provider Development Guide](./PROVIDER_DEVELOPMENT.md)
4. **Join the Community**: [GitHub](https://github.com/kubiya-ai)

## Troubleshooting

### Common Issues

1. **API Key Invalid**
   - Ensure your API key is correctly set
   - Check expiration date
   - Verify organization access

2. **Connection Errors**
   - Check network connectivity
   - Verify API URL is correct
   - Check firewall settings

3. **Workflow Execution Fails**
   - Verify runner availability
   - Check integration permissions
   - Review workflow syntax

### Getting Help

- Documentation: [docs.kubiya.ai](https://docs.kubiya.ai)
- Support: support@kubiya.ai

