"""
Example usage of the Stacks service for managing Terraform stacks

This example demonstrates:
1. Creating stack files with direct content
2. Creating stack files from file paths  
3. Base64 encoding of file content in API requests
4. Proper exception handling for stack operations
"""

from kubiya_workflow_sdk.kubiya_services.client import KubiyaClient
from kubiya_workflow_sdk.kubiya_services.services.stacks import StackRequest, StackFiles
from kubiya_workflow_sdk.kubiya_services.exceptions import StackPlanError, StackApplyError, StackStreamError


def stacks_example():
    """Example of using the stacks service"""
    # Initialize the client
    client = KubiyaClient(
        api_key="your-api-key",
        base_url="https://api.kubiya.ai"
    )
    
    # Create stack files - Example 1: Using direct content
    stack_files_content = StackFiles(
        main_tf="""
        terraform {
          required_providers {
            local = {
              source  = "hashicorp/local"
              version = "~> 2.1"
            }
            random = {
              source  = "hashicorp/random"
              version = "~> 3.1"
            }
          }
        }

        # Generate random values
        resource "random_id" "server_id" {
          byte_length = 4
        }

        resource "random_password" "db_password" {
          length  = var.password_length
          special = true
        }
        
        resource "random_pet" "server_names" {
          count  = var.server_count
          length = 2
        }

        # Create configuration file
        resource "local_file" "app_config" {
          content = <<-EOF
        [app]
        name = ${var.app_name}
        environment = ${var.environment}
        version = ${var.app_version}
        
        [database]
        host = localhost
        port = 5432
        password = ${random_password.db_password.result}

        [servers]
        %{ for i, name in random_pet.server_names ~}
        ${name.id} = 192.168.1.${10 + i}:${var.base_port + i}
        %{ endfor ~}
        
        [settings]
        debug = ${var.debug_mode}
        ssl_enabled = ${var.enable_ssl}
        log_level = ${var.log_level}
        EOF
        
          filename = "generated_config.ini"
        }

        # Create JSON output file
        resource "local_file" "server_info" {
          content = jsonencode({
            project_id = random_id.server_id.hex
            servers = [
              for i, name in random_pet.server_names : {
                name = name.id
                ip   = "192.168.1.${10 + i}"
                port = var.base_port + i
              }
            ]
            database = {
              host     = "localhost"
              port     = 5432
              password = random_password.db_password.result
            }
            created_at = timestamp()
          })
          
          filename = "server_info.json"
        }
        """,

        variables_tf="""
            variable "app_name" {
              description = "Name of the application"
              type        = string
              default     = "test-app"
            }

            variable "environment" {
              description = "Environment (dev, test, prod)"
              type        = string
              default     = "dev"
              
              validation {
                condition     = contains(["dev", "test", "prod"], var.environment)
                error_message = "Environment must be dev, test, or prod."
              }
            }

            variable "app_version" {
              description = "Application version"
              type        = string
              default     = "1.0.0"
            }
            
            variable "server_count" {
              description = "Number of servers"
              type        = number
              default     = 3
              
              validation {
                condition     = var.server_count >= 1 && var.server_count <= 10
                error_message = "Server count must be between 1 and 10."
              }
            }

            variable "base_port" {
              description = "Base port number for servers"
              type        = number
              default     = 8080
            }
            
            variable "password_length" {
              description = "Length of generated password"
              type        = number
              default     = 16
            }
            
            variable "debug_mode" {
              description = "Enable debug mode"
              type        = bool
              default     = false
            }
            
            variable "enable_ssl" {
              description = "Enable SSL"
              type        = bool
              default     = true
            }

            variable "log_level" {
              description = "Logging level"
              type        = string
              default     = "INFO"
              
              validation {
                condition     = contains(["DEBUG", "INFO", "WARN", "ERROR"], var.log_level)
                error_message = "Log level must be DEBUG, INFO, WARN, or ERROR."
              }
            }
        """
    )

    # Use the content-based example for this demo
    stack_files = stack_files_content
    
    # Create stack request
    stack_request = StackRequest(
        name="example-stack",
        files=stack_files
    )
    
    try:
        # Plan the stack
        print("Planning stack...")
        plan_result = client.stacks.plan(stack_request)
        print(f"Plan result: {plan_result}")
    
    except StackPlanError as e:
        print(f"Plan failed: {e}")
        if e.details.get("validation_errors"):
            validation_errors = e.details["validation_errors"]
            print(f"Error message: {validation_errors.get('errorMessage', 'N/A')}")
            if validation_errors.get("initOutput"):
                print(f"Init output: {validation_errors['initOutput']}")
            if validation_errors.get("planOutput"):
                print(f"Plan output: {validation_errors['planOutput']}")
        return
    
    try:
        # Apply the stack
        print("Applying stack...")
        apply_result = client.stacks.apply(stack_request)
        print(f"Apply result: {apply_result}")
        
    except StackApplyError as e:
        print(f"Apply failed: {e}")
        if e.details.get("terraform_errors"):
            terraform_errors = e.details["terraform_errors"]
            print(f"Error message: {terraform_errors.get('errorMessage', 'N/A')}")
            if terraform_errors.get("initOutput"):
                print(f"Init output: {terraform_errors['initOutput']}")
            if terraform_errors.get("applyOutput"):
                print(f"Apply output: {terraform_errors['applyOutput']}")
        return

    # If apply returns a stack_id, stream the logs
    try:
        print(f"Streaming logs for stack {apply_result.get('uuid')}...")
        for log_line in client.stacks.stream():
            print(f"Log: {log_line}")
    except StackStreamError as e:
        print(f"Streaming failed: {e}")
        if e.details.get("stream_position"):
            print(f"Failed at stream position: {e.details['stream_position']}")


if __name__ == "__main__":
    stacks_example()