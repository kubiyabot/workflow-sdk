# Kubiya Workflow SDK

<div align="center">

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io)
[![Docker](https://img.shields.io/badge/Docker-Powered-blue.svg)](https://docker.com)

**Build Deterministic AI Workflows That Actually Work™**

[Get Started](#-quick-start) • [MCP Server](#-mcp-model-context-protocol) • [Documentation](https://docs.kubiya.ai) • [Examples](#-examples) • [API Reference](#-api-reference)

</div>

---

## 🚀 The Future of AI is Deterministic

**Kubiya Workflow SDK** is a serverless workflow platform that transforms unpredictable AI agents into reliable, production-grade automation. Every workflow step runs as an independent Docker container, giving you the power to run ANY software while maintaining deterministic execution.

### Why We Built This

After watching teams struggle with free-wheeling agent frameworks that promise magic but deliver chaos, we took a different approach. Instead of hoping an AI will figure out the right sequence of actions, we provide the tools to **define** the right sequence – with AI filling in the intelligent parts. [Read more about our architecture →](docs/ARCHITECTURE.md)

### Core Principles

- **🐳 Serverless Containers**: Every step runs in its own Docker container - use ANY language, tool, or software
- **🎯 Deterministic Execution**: Same inputs → Same workflow → Same outputs, every time
- **🏗️ Stateless Architecture**: Each execution starts fresh with zero state pollution
- **🚀 Infinite Scale**: From 1 to 1,000,000 executions without infrastructure changes
- **🤖 MCP Compatible**: Works with Claude Desktop, ChatGPT, and any MCP client
- **🏠 Your Infrastructure**: Runs entirely on-premise with zero vendor lock-in

## ✨ Key Features

### 🎯 Stateless & Serverless Orchestration
```yaml
# Workflows are pure schemas - no hidden state
name: incident-response
steps:
  - name: detect
    executor: docker
    image: monitoring:latest
  - name: analyze  
    executor: inline_agent
    depends: [detect]
  - name: remediate
    executor: shell
    depends: [analyze]
```

### 🔌 Universal Integration

```python
# Via Kubiya API
client.execute_workflow("deploy-app", params={"version": "2.0"})

# Via MCP Server (works with ANY agent system)
mcp_client.call_tool("execute_workflow", workflow_input="deploy-app")

# Via Agent Server (OpenAI-compatible)
response = openai.chat.completions.create(
    model="kubiya-workflow-agent",
    messages=[{"role": "user", "content": "Deploy version 2.0"}]
)

# Direct in your code
result = workflow.run(params={"env": "production"})
```

## 📦 Installation

```bash
# Basic installation
pip install kubiya-workflow-sdk

# With all features (includes MCP server and agent capabilities)
pip install kubiya-workflow-sdk[all]

# For development
pip install kubiya-workflow-sdk[dev]
```

### 🐳 Docker Installation

```bash
# Using Docker Compose (recommended)
docker-compose up -d

# Or run the MCP Agent Server directly
docker run -p 8000:8000 \
  -e KUBIYA_API_KEY=$KUBIYA_API_KEY \
  -e TOGETHER_API_KEY=$TOGETHER_API_KEY \
  kubiya/workflow-sdk:latest \
  mcp agent --provider together --port 8000
```

## 🤖 MCP (Model Context Protocol)

Kubiya SDK includes a powerful MCP implementation that enables ANY AI system to create and execute workflows.

### Quick Start: MCP Agent Server

The fastest way to get started is with our Agent Server - an OpenAI-compatible API that any AI can use:

```bash
# Start the agent server
kubiya mcp agent --provider together --port 8000

# Or with a specific model
kubiya mcp agent --provider anthropic --model claude-3-5-sonnet-20241022 --port 8000
```

Now ANY OpenAI-compatible client can create workflows:

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="not-needed"  # Uses env vars for actual API keys
)

response = client.chat.completions.create(
    model="kubiya-workflow-agent",
    messages=[{
        "role": "user", 
        "content": "Create a workflow that backs up all databases to S3"
    }],
    stream=True
)

for chunk in response:
    print(chunk.choices[0].delta.content, end="")
```

### MCP Tools Available

The MCP server provides these tools to AI agents:

#### 1. **compile_workflow** - Convert DSL to workflow manifest
```python
# AI agents can write simple DSL code
dsl_code = """
from kubiya_workflow_sdk.dsl import Workflow

wf = Workflow("backup-databases")
wf.description("Backup all databases to S3")
wf.step("backup-postgres", "pg_dump -h $DB_HOST > backup.sql")
wf.step("upload-to-s3", "aws s3 cp backup.sql s3://backups/")
"""

result = compile_workflow(dsl_code=dsl_code)
# Returns: {"success": true, "manifest": {...}}
```

#### 2. **execute_workflow** - Run workflows with real-time streaming
```python
# Execute with streaming events
result = execute_workflow(
    workflow_input={"name": "backup-databases", "steps": [...]},
    stream_format="vercel"  # or "raw" for standard events
)
# Streams: step_running, step_complete, workflow_complete events
```

#### 3. **get_workflow_runners** - List available execution environments
```python
runners = get_workflow_runners()
# Returns Docker-enabled runners, Kubernetes runners, etc.
```

#### 4. **get_integrations** - Discover available integrations
```python
integrations = get_integrations(category="cloud")
# Returns AWS, GCP, Azure integrations with configs
```

#### 5. **get_workflow_secrets** - Manage secure credentials
```python
secrets = get_workflow_secrets(pattern="AWS_*")
# Returns available secrets for workflows
```

### Claude Desktop Integration

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "kubiya": {
      "command": "kubiya",
      "args": ["mcp", "server"],
      "env": {
        "KUBIYA_API_KEY": "your-api-key"
      }
    }
  }
}
```

Now Claude can create and execute workflows directly!

### Vercel AI SDK Integration

```typescript
import { openai } from '@ai-sdk/openai';
import { streamText } from 'ai';

const result = await streamText({
  model: openai('kubiya-workflow-agent', {
    baseURL: 'http://localhost:8000/v1',
  }),
  messages: [
    {
      role: 'user',
      content: 'Create a CI/CD pipeline for my Node.js app',
    },
  ],
});

// Handle streaming with proper event parsing
for await (const chunk of result.textStream) {
  // Vercel format: 0:"text" or 2:{"type":"step_running",...}
  console.log(chunk);
}
```

### Direct MCP Server Usage

For lower-level control, use the MCP server directly:

```bash
# Start MCP server (stdio transport)
kubiya mcp server

# The server communicates via stdio, perfect for tool integration
```

## 🎯 Quick Start

### 1. Start the Agent Server

```bash
# Set your API keys
export KUBIYA_API_KEY="your-key"
export TOGETHER_API_KEY="your-key"  # Or OPENAI_API_KEY, ANTHROPIC_API_KEY

# Start the server
kubiya mcp agent --provider together --port 8000
```

### 2. Create a Workflow with AI

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="not-needed")

# Ask AI to create a workflow
response = client.chat.completions.create(
    model="kubiya-workflow-agent",
    messages=[{
        "role": "user",
        "content": """
        Create a workflow that:
        1. Checks disk space on all servers
        2. Alerts if any disk is over 80% full
        3. Automatically cleans up old logs if needed
        """
    }]
)

print(response.choices[0].message.content)
```

### 3. Execute the Workflow

The AI will automatically execute the workflow and stream results in real-time!

## 🏗️ Architecture

### MCP Server Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   AI Clients    │────▶│   Agent Server   │────▶│   MCP Server    │
│ (Claude, GPT-4) │     │  (OpenAI API)    │     │   (Tools)       │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                │                          │
                                ▼                          ▼
                        ┌──────────────────┐     ┌─────────────────┐
                        │  Kubiya API      │     │  Workflow       │
                        │  (Execution)     │     │  Engine         │
                        └──────────────────┘     └─────────────────┘
```

### Workflow Execution Flow

1. **AI generates DSL** → Simple, readable workflow code
2. **MCP compiles** → Validates and converts to manifest
3. **Kubiya executes** → Runs in Docker containers
4. **Streams events** → Real-time progress updates

## 🛠️ CLI Commands

### MCP Commands

```bash
# Start agent server (OpenAI-compatible API)
kubiya mcp agent --provider anthropic --model claude-3-opus --port 8000

# Start MCP server (stdio transport for tools)
kubiya mcp server

# Interactive chat mode for testing
kubiya mcp chat --provider together

# Test MCP tools
kubiya mcp test
```

### Workflow Commands

```bash
# Validate a workflow
kubiya validate workflow.py

# Execute a workflow
kubiya run workflow.py --params KEY=value

# List executions
kubiya list --limit 10

# Stream execution logs
kubiya logs <execution-id> --follow
```

## 📊 Examples

### Create a Monitoring Workflow

```python
# The AI can generate this from a simple description
from kubiya_workflow_sdk.dsl import Workflow

wf = Workflow("system-monitor")
wf.description("Monitor system health and alert on issues")

# Check CPU usage
wf.step("check-cpu", """
    cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
    if (( $(echo "$cpu_usage > 80" | bc -l) )); then
        echo "HIGH_CPU_ALERT: ${cpu_usage}%"
    fi
""")

# Check memory
wf.step("check-memory", """
    mem_usage=$(free | grep Mem | awk '{print ($3/$2) * 100.0}')
    if (( $(echo "$mem_usage > 80" | bc -l) )); then
        echo "HIGH_MEMORY_ALERT: ${mem_usage}%"
    fi
""")

# Send alerts
wf.step("send-alerts")
  .condition("${check-cpu.output} contains 'ALERT' or ${check-memory.output} contains 'ALERT'")
  .shell("curl -X POST $SLACK_WEBHOOK -d '{\"text\": \"System Alert: $OUTPUT\"}'")
```

### Multi-Language Data Pipeline

```python
# AI can orchestrate complex multi-language workflows
wf = Workflow("data-pipeline")

# Python for data extraction
wf.step("extract")
  .docker("python:3.11-slim")
  .packages(["pandas", "requests"])
  .code("""
import pandas as pd
data = pd.read_csv('https://data.source/file.csv')
data.to_parquet('/tmp/data.parquet')
""")

# R for statistical analysis  
wf.step("analyze")
  .docker("r-base:latest")
  .code("""
library(arrow)
data <- read_parquet('/tmp/data.parquet')
summary_stats <- summary(data)
write.csv(summary_stats, '/tmp/analysis.csv')
""")

# Node.js for API upload
wf.step("upload")
  .docker("node:20-slim")
  .code("""
const fs = require('fs');
const axios = require('axios');

const data = fs.readFileSync('/tmp/analysis.csv');
await axios.post('https://api.destination/upload', data);
""")
```

## 🚀 Production Deployment

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kubiya-agent-server
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: agent-server
        image: kubiya/workflow-sdk:latest
        command: ["kubiya", "mcp", "agent"]
        args: ["--provider", "anthropic", "--port", "8000"]
        env:
        - name: KUBIYA_API_KEY
          valueFrom:
            secretKeyRef:
              name: kubiya-secrets
              key: api-key
        ports:
        - containerPort: 8000
```

### Docker Compose

```yaml
version: '3.8'
services:
  agent-server:
    image: kubiya/workflow-sdk:latest
    command: kubiya mcp agent --provider together --port 8000
    ports:
      - "8000:8000"
    environment:
      - KUBIYA_API_KEY=${KUBIYA_API_KEY}
      - TOGETHER_API_KEY=${TOGETHER_API_KEY}
    restart: unless-stopped
```

## 📚 Documentation

### 🚀 Getting Started
- [Installation Guide](docs/kubiya/getting-started/installation.mdx)
- [MCP Quickstart](docs/kubiya/mcp/quickstart.mdx)
- [Your First Workflow](docs/kubiya/getting-started/quickstart.mdx)

### 🤖 MCP Documentation
- [MCP Overview](docs/kubiya/mcp/overview.mdx) - Understanding Model Context Protocol
- [Agent Server Guide](docs/kubiya/mcp/agent-server.mdx) - OpenAI-compatible API
- [MCP Tools Reference](docs/kubiya/mcp/tools-reference.mdx) - Available MCP tools
- [Authentication](docs/kubiya/mcp/authentication.mdx) - API keys and security
- [Integration Examples](docs/kubiya/mcp/examples.mdx) - Claude, ChatGPT, Vercel AI

### 🏗️ Workflow Development
- [DSL Reference](docs/kubiya/workflows/dsl-reference.mdx) - Workflow syntax
- [Docker Steps](docs/kubiya/workflows/docker-steps.mdx) - Container execution
- [Testing Workflows](docs/kubiya/workflows/testing.mdx) - Test and debug

### 📡 API Reference
- [REST API](docs/kubiya/api-reference/rest.mdx) - HTTP endpoints
- [Streaming Events](docs/kubiya/api-reference/streaming.mdx) - SSE and Vercel formats
- [Client SDK](docs/kubiya/api-reference/client.mdx) - Python client

## 🤝 Support

- 📖 [Documentation](https://docs.kubiya.ai)
- 🐛 [Issue Tracker](https://github.com/kubiyabot/workflow-sdk/issues)
- 📧 [Enterprise Support](https://kubiya.ai/contact)

## 📄 License

MIT - See [LICENSE](LICENSE) for details.

---


<div align="center">

**Stop hoping AI agents will work. Start shipping workflows that do.**

[Get Started](#-quick-start) • [MCP Docs](#-mcp-model-context-protocol) • [Examples](#-examples)

</div> 
