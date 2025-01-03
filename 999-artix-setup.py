import subprocess
import yaml
import os
import sys
import shutil
import tempfile
from datetime import datetime
import logging
import argparse  # Import argparse for command-line arguments

# Set up argument parser
parser = argparse.ArgumentParser(
    description="Artix setup script. This script requires a YAML configuration file to execute the specified tasks.",
    epilog="Use the --debug flag to enable verbose logging for debugging purposes."
)
parser.add_argument("yaml_file", help="Path to the YAML configuration file")
parser.add_argument("--debug", action="store_true", help="Enable verbose logging")
args = parser.parse_args()

# Configure logging
logging_level = logging.DEBUG if args.debug else logging.INFO
logging.basicConfig(level=logging_level)
logger = logging.getLogger(__name__)

import time  # Import the time module

def execute_shell(commands, sudo=False, retries=3, delay=5):
    logger.debug(f"Starting execute_shell with commands: {commands}, sudo: {sudo}, retries: {retries}, delay: {delay}")
    for command in commands:
        attempt = 0

        while attempt < retries:
            try:
                if sudo:
                    command = f"sudo {command}"
                logger.info(f"Executing: {command}")
                subprocess.run(command, shell=True, check=True, timeout=120)  # Adjust the timeout as needed
                break
            except subprocess.CalledProcessError as e:
                attempt += 1
                logger.error(f"Error executing command: {command}")
                if attempt == retries:
                    logger.error(f"Command failed after {retries} attempts: {command}")
                    user_input = input(f"Command failed after {retries} attempts: {command}. Do you want to continue? (yes/no): ")
                    if user_input.lower() == "yes":
                        logger.info("User chose to continue.")
                        break
                    else:
                        logger.info("User chose to stop execution.")
                        return
                logger.info(f"Retrying ({attempt}/{retries}): {command}")
                time.sleep(delay)  # Add a delay before retrying

def execute_python(script, *args, sudo=False):
    """
    Executes a Python script with optional arguments.
    :param script: Path to the Python script to execute.
    :param args: Arguments to pass to the script.
    :param sudo: Whether to run the command with sudo.
    """
    logger.debug(f"Starting execute_python with script: {script}, args: {args}, sudo: {sudo}")
    command = "python3"
    if sudo:
        command = f"sudo {command}"
    try:
        full_command = f"{command} {script} {' '.join(args)}"
        logger.info(f"Executing Python script: {full_command}")
        subprocess.run(full_command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error executing Python script: {full_command}")
        logger.error(e)

def install_packages(packages, command_template, sudo=False):
    logger.debug(f"Starting install_packages with packages: {packages}, command_template: {command_template}, sudo: {sudo}")
    for package in packages:
        command = command_template.format(package=package)
        execute_shell([command], sudo)

def write_to_file(filepath, content, sudo=False, backup=False):
    logger.debug(f"Starting write_to_file with filepath: {filepath}, sudo: {sudo}, backup: {backup}")
    try:
        logger.info(f"Preparing to write to file: {filepath}")
        dir_path = os.path.dirname(filepath)
        if sudo:
            execute_shell([f"sudo mkdir -p {dir_path}"])
        else:
            os.makedirs(dir_path, exist_ok=True)

        # Check if the file exists
        if os.path.exists(filepath) and backup:
            # Create a backup
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            backup_filepath = f"{filepath}.{timestamp}"
            logger.info(f"File exists. Creating backup: {backup_filepath}")
            if sudo:
                execute_shell([f"sudo cp {filepath} {backup_filepath}"])
            else:
                shutil.copy(filepath, backup_filepath)

        # Write to a temporary file in /tmp if sudo is required
        temp_path = f"/tmp/{os.path.basename(filepath)}"
        with open(temp_path, "w") as temp_file:
            temp_file.write(content)

        # Move the temporary file to the final location
        if sudo:
            execute_shell([f"sudo mv {temp_path} {filepath}"])
        else:
            os.replace(temp_path, filepath)

        logger.info(f"Successfully wrote to file: {filepath}")

    except Exception as e:
        logger.error(f"Error writing to file: {filepath}")
        logger.error(e)

def setup_service(service_name, service_config, paths):
    """
    Dynamically handles the 'setup_service' section from the YAML file.
    :param service_name: Name of the service (e.g., 'bluetoothd').
    :param service_config: Dictionary containing the service configuration.
    :param paths: Dictionary containing path placeholders (e.g., service_path, sv_path).
    """
    logger.debug(f"Starting setup_service with service_name: {service_name}, service_config: {service_config}, paths: {paths}")

    placeholders = {
        "service_path": paths.get("service_path", "/run/runit/service/"),
        "sv_path": paths.get("sv_path", "/etc/runit/sv/"),
        "service_name": service_name,
    }

    # Handle packages installation
    if "packages" in service_config:
        packages = service_config["packages"]
        package_command = packages.get("command", "sudo pacman -S {package} --needed --noconfirm")
        for package in packages.get("package", []):
            execute_shell([package_command.format(package=package)])

    # Handle path initialization
    if service_config.get("path_init", False):
        path_init_commands = [
            'sudo rm -f {service_path}{service_name}',
            'sudo mkdir -p {sv_path}{service_name}',
            'sudo mkdir -p {sv_path}{service_name}/log',
            'sudo mkdir -p {sv_path}{service_name}/log/main',
        ]
        for cmd in path_init_commands:
            execute_shell([cmd.format(**placeholders)])

    # Handle run and log file creation
    for file_type, file_config in [("run_file", "run"), ("log_file", "log/run")]:
        if file_type in service_config:
            file_path = f"{placeholders['sv_path']}{service_name}/{file_config}"
            file_content = service_config[file_type]["content"]
            write_to_file(file_path, file_content, sudo=True)
            execute_shell([f"sudo chmod +x {file_path}"])

    # Handle service initialization
    if service_config.get("service_init", False):
        service_init_commands = [
            'sudo chmod +x {sv_path}{service_name}/run',
            'sudo chmod +x {sv_path}{service_name}/log/run',
            'sudo ln -s {sv_path}{service_name} {service_path}',
            'sudo sv start {service_name}',
        ]
        for cmd in service_init_commands:
            execute_shell([cmd.format(**placeholders)], sudo=True)

    logger.info(f"Service {service_name} setup completed.")

def parse_and_execute(yaml_content, debug=False):
    """
    Parses the YAML content and executes tasks based on its structure.
    """
    logger.debug(f"Starting parse_and_execute with yaml_content: {yaml_content}")
    for task_name, task_config in yaml_content.items():
        logger.info(f"Processing: {task_name}")

        if task_name == "service_paths":
            continue  # Skip the paths configuration

        # Install Packages
        if "packages" in task_config:
            install_packages(
                task_config["packages"].get("package", []),
                task_config["packages"].get("command", "sudo pacman -S {package} --needed --noconfirm")
            )

        # Setup Service
        if "setup_service" in task_config:
            service_paths = yaml_content.get("service_paths", {})
            service_name = task_config.get("service_name", task_name)
            setup_service(service_name, task_config["setup_service"], service_paths)

        # Execute General Shell Commands
        if "shell" in task_config:
            execute_shell(task_config["shell"])

        # Execute Python Scripts
        if "python" in task_config:
            if isinstance(task_config["python"], dict):
                execute_python(
                    task_config["python"].get("script", ""),
                    *task_config["python"].get("parameters", [])
                )

        # Handle File Creation
        if "file" in task_config:
            file_config = task_config["file"]
            if isinstance(file_config, dict):
                if "name" in file_config and "content" in file_config:
                    logger.info(f"Attempting to write file: {file_config['name']}")
                    write_to_file(
                        file_config["name"],
                        file_config["content"],
                        sudo=True,
                        backup=True
                    )
                else:
                    logger.error("File entry is missing 'name' or 'content'. Skipping.")
            else:
                logger.error(f"Invalid structure under 'file' key in task: {task_name}.")

        logger.info(f"Finished: {task_name}\n")

if __name__ == "__main__":
    # Ensure a YAML file is provided
    if not args.yaml_file:
        logger.error("No YAML file provided. Use --help for usage information.")
        sys.exit(1)

    # Parse and execute the provided YAML file
    yaml_file_path = args.yaml_file

    try:
        with open(yaml_file_path, "r") as file:
            yaml_content = yaml.safe_load(file)
        parse_and_execute(yaml_content)
    except FileNotFoundError:
        logger.error(f"YAML file not found: {yaml_file_path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML file: {e}")
        sys.exit(1)
