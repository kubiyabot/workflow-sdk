"""
Workflow builder with full feature support.

Supports all Kubiya workflow capabilities:
- Chain and graph execution types
- Environment variables and parameters
- Scheduling and queue management
- Email notifications
- Lifecycle handlers
- And more...
"""

from typing import Dict, Any, List, Optional, Union, Callable
from enum import Enum
import yaml
import json
from kubiya_workflow_sdk.dsl.step import Step


class WorkflowType(str, Enum):
    """Workflow execution types."""

    CHAIN = "chain"  # Sequential with automatic dependencies
    GRAPH = "graph"  # Explicit dependencies required


class Workflow:
    """
    Main workflow builder with fluent API.

    Example:
        wf = (Workflow("data-pipeline")
              .description("Daily ETL pipeline")
              .type("chain")  # or "graph"
              .schedule("0 2 * * *")
              .env(LOG_LEVEL="info", DATA_DIR="/data")
              .params(DATE="`date '+%Y-%m-%d'`", BATCH_SIZE="1000")
              .step("extract", "wget data.csv")
              .step("process", "python process.py"))
    """

    def __init__(self, name: str):
        self.data = {"name": name, "steps": []}
        self._current_type = WorkflowType.CHAIN

    def description(self, desc: str) -> "Workflow":
        """Set workflow description."""
        self.data["description"] = desc
        return self

    def type(self, workflow_type: str) -> "Workflow":
        """Set workflow type: 'chain' or 'graph'."""
        self._current_type = WorkflowType(workflow_type)
        self.data["type"] = workflow_type
        return self

    def runner(self, runner_name: str) -> "Workflow":
        """Set the runner for workflow execution."""
        self.data["runner"] = runner_name
        return self

    def schedule(self, cron: str) -> "Workflow":
        """Set cron schedule."""
        self.data["schedule"] = cron
        return self

    def env(self, **variables) -> "Workflow":
        """Set environment variables."""
        self.data["env"] = variables
        return self

    def params(self, **parameters) -> "Workflow":
        """Set parameters with defaults."""
        self.data["params"] = parameters
        return self

    def with_files(self, files: Dict[str, str]) -> "Workflow":
        """Add files to the workflow.
        
        Args:
            files: Dictionary mapping filename to content
            
        Example:
            wf.with_files({
                "config.json": '{"key": "value"}',
                "script.py": '''
import pandas as pd
print("Hello from script")
'''
            })
        """
        self.data["files"] = files
        return self

    def dotenv(self, *files: str) -> "Workflow":
        """Load environment from .env files."""
        if len(files) == 1:
            self.data["dotenv"] = files[0]
        else:
            self.data["dotenv"] = list(files)
        return self

    def step(self, name: str, command: Optional[str] = None, *, callback: Optional[Callable[[Step], None]] = None,  **kwargs) -> "Workflow":
        """Add a basic step."""
        step = Step(name, command, **kwargs)
        if callback:
            callback(step)

        self.data["steps"].append(step.to_dict())
        return self

    def get_secret_step(self, name: str, secret_name: str, **kwargs) -> "Workflow":
        """Add a get_secret step for retrieving secrets."""
        step_data = {"name": name, "type": "get_secret", "secret_name": secret_name, **kwargs}
        self.data["steps"].append(step_data)
        return self

    def parallel_steps(
        self,
        name: str,
        items: List[Any],
        command: str,
        max_concurrent: Optional[int] = None,
        **kwargs,
    ) -> "Workflow":
        """Add parallel execution steps."""
        from .step import Step

        step = Step(name, command, **kwargs)
        parallel_config = {"items": items}
        if max_concurrent:
            parallel_config["maxConcurrent"] = max_concurrent
        step.parallel(parallel_config)
        self.data["steps"].append(step.to_dict())
        return self

    def sub_workflow(
        self, name: str, workflow: str, params: Optional[str] = None, **kwargs
    ) -> "Workflow":
        """Add sub-workflow step."""
        from .step import Step

        step = Step(name, run=workflow, params=params, **kwargs)
        self.data["steps"].append(step.to_dict())
        return self

    # Queue management
    def queue(self, queue_name: str, max_active_runs: Optional[int] = None) -> "Workflow":
        """Assign to queue."""
        self.data["queue"] = queue_name
        if max_active_runs is not None:
            self.data["maxActiveRuns"] = max_active_runs
        return self

    def max_active_runs(self, limit: int) -> "Workflow":
        """Set max concurrent runs (-1 for unlimited)."""
        self.data["maxActiveRuns"] = limit
        return self

    def max_active_steps(self, limit: int) -> "Workflow":
        """Set max concurrent steps."""
        self.data["maxActiveSteps"] = limit
        return self

    # Execution control
    def skip_if_successful(self, skip: bool = True) -> "Workflow":
        """Skip if already succeeded today."""
        self.data["skipIfSuccessful"] = skip
        return self

    def timeout(self, seconds: int) -> "Workflow":
        """Set workflow timeout."""
        self.data["timeout"] = seconds
        return self

    def cleanup_timeout(self, seconds: int) -> "Workflow":
        """Set cleanup timeout."""
        self.data["maxCleanUpTimeSec"] = seconds
        return self

    def delay(self, seconds: int) -> "Workflow":
        """Delay workflow start."""
        self.data["delaySec"] = seconds
        return self

    def max_output_size(self, bytes: int) -> "Workflow":
        """Set max output size in bytes."""
        self.data["maxOutputSize"] = bytes
        return self

    # Lifecycle handlers
    def handlers(
        self,
        success: Optional[str] = None,
        failure: Optional[str] = None,
        exit: Optional[str] = None,
        cancel: Optional[str] = None,
    ) -> "Workflow":
        """Set lifecycle handlers."""
        handlers = {}
        if success:
            handlers["success"] = {"command": success}
        if failure:
            handlers["failure"] = {"command": failure}
        if exit:
            handlers["exit"] = {"command": exit}
        if cancel:
            handlers["cancel"] = {"command": cancel}

        if handlers:
            self.data["handlerOn"] = handlers
        return self

    # Email notifications
    def notifications(
        self,
        mail_on_failure: bool = True,
        mail_on_success: bool = False,
        smtp: Optional[Dict[str, str]] = None,
        error_mail: Optional[Dict[str, Any]] = None,
        info_mail: Optional[Dict[str, Any]] = None,
    ) -> "Workflow":
        """Configure email notifications."""
        self.data["mailOn"] = {"failure": mail_on_failure, "success": mail_on_success}

        if smtp:
            self.data["smtp"] = smtp
        if error_mail:
            self.data["errorMail"] = error_mail
        if info_mail:
            self.data["infoMail"] = info_mail

        return self

    # Metadata
    def tags(self, *tags: str) -> "Workflow":
        """Add tags."""
        self.data["tags"] = ",".join(tags)
        return self

    def group(self, group_name: str) -> "Workflow":
        """Set workflow group."""
        self.data["group"] = group_name
        return self

    # Preconditions
    def preconditions(self, *conditions: Union[str, Dict[str, str]]) -> "Workflow":
        """Add workflow-level preconditions."""
        self.data["preconditions"] = list(conditions)
        return self

    # Export methods
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.data

    def to_yaml(self) -> str:
        """Convert to YAML."""
        return yaml.dump(self.data, default_flow_style=False, sort_keys=False)

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON."""
        return json.dumps(self.data, indent=indent)

    def validate(self) -> Dict[str, Any]:
        """Basic validation."""
        errors = []
        warnings = []

        if not self.data.get("name"):
            errors.append("Workflow name is required")

        if not self.data.get("steps"):
            errors.append("At least one step is required")

        # Check step names
        step_names = [s.get("name") for s in self.data.get("steps", [])]
        if len(step_names) != len(set(step_names)):
            errors.append("Duplicate step names found")

        # Check dependencies in chain mode
        if self._current_type == WorkflowType.CHAIN:
            for step in self.data.get("steps", []):
                if step.get("depends"):
                    warnings.append(
                        f"Step '{step['name']}' has explicit dependencies in chain mode"
                    )

        # Validate step structure
        for i, step in enumerate(self.data.get("steps", [])):
            if not step.get("name"):
                errors.append(f"Step {i+1} is missing a name")

            # Must have command, run, or type
            if not any([step.get("command"), step.get("run"), step.get("type")]):
                errors.append(f"Step '{step.get('name', i+1)}' needs 'command', 'run', or 'type'")

            # Validate retry configuration if present
            if retry := step.get("retry"):
                if not isinstance(retry, dict):
                    errors.append(f"Step '{step.get('name', i+1)}': retry must be a dictionary")
                elif "max_attempts" in retry and not isinstance(retry["max_attempts"], int):
                    errors.append(
                        f"Step '{step.get('name', i+1)}': retry.max_attempts must be an integer"
                    )

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


# Convenience functions
def workflow(name: str) -> Workflow:
    """Create a new workflow."""
    return Workflow(name)


def chain(name: str) -> Workflow:
    """Create a chain workflow (sequential)."""
    return Workflow(name).type("chain")


def graph(name: str) -> Workflow:
    """Create a graph workflow (explicit dependencies)."""
    return Workflow(name).type("graph")
