"""
Example demonstrating file-based Terraform stack deployment
"""
import tempfile
from pathlib import Path

from kubiya_workflow_sdk import KubiyaClient
from kubiya_workflow_sdk.kubiya_services.services.stacks import StackRequest, StackFiles
from kubiya_workflow_sdk.kubiya_services.exceptions import StackPlanError, StackApplyError, StackStreamError


def create_terraform_files():
    """Create temporary Terraform files for demonstration"""
    
    # Create temporary directory for Terraform files
    temp_dir = Path(tempfile.mkdtemp())
    
    # Create main.tf
    main_tf_content = """
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
        """
    
    # Create variables.tf
    variables_tf_content = """
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
    
    # Write files
    main_tf_path = temp_dir / "main.tf"
    variables_tf_path = temp_dir / "variables.tf"
    
    main_tf_path.write_text(main_tf_content)
    variables_tf_path.write_text(variables_tf_content)
    
    return main_tf_path, variables_tf_path, temp_dir


def file_based_stack_example():
    """Example using file paths instead of direct content"""

    # Initialize the client
    client = KubiyaClient(
        api_key="your-api-key",
        base_url="https://api.kubiya.ai"
    )
    
    print("Creating temporary Terraform files...")
    main_tf_path, variables_tf_path, temp_dir = create_terraform_files()
    
    print(f"Files created in: {temp_dir}")
    print(f"- main.tf: {main_tf_path}")
    print(f"- variables.tf: {variables_tf_path}")
    
    try:
        # Create stack files using file paths
        stack_files = StackFiles(
            main_tf_path=main_tf_path,
            variables_tf_path=variables_tf_path
        )
        
        # Create stack request
        stack_request = StackRequest(
            name="file-based-stack",
            files=stack_files
        )
        
        print("\n=== Testing file content reading ===")
        main_content = stack_files.get_main_tf_content()
        vars_content = stack_files.get_variables_tf_content()
        print(f"Main.tf content length: {len(main_content)} characters")
        print(f"Variables.tf content length: {len(vars_content)} characters")

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
        stack_id = apply_result.get("uuid")
        if stack_id:
            try:
                print(f"Streaming logs for stack {stack_id}...")
                for log_line in client.stacks.stream(stack_id):
                    print(f"Log: {log_line}")
            except StackStreamError as e:
                print(f"Streaming failed: {e}")
                if e.details.get("stream_position"):
                    print(f"Failed at stream position: {e.details['stream_position']}")
        else:
            print("No stack_id returned from apply operation")



    except FileNotFoundError as e:
        print(f"File not found: {e}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Cleanup temporary files
        import shutil
        shutil.rmtree(temp_dir)
        print(f"\nCleaned up temporary directory: {temp_dir}")


if __name__ == "__main__":
    file_based_stack_example()