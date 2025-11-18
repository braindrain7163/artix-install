# Copilot Instructions

## Project Snapshot
- Automates Artix Linux installs with interactive Bash stages (`000-` to `115-`) plus YAML-driven post-install automation.
- Runs on systemd-free Artix; most scripts assume `runit` service supervision but offer `dinit` fallbacks where noted.
- Expect root access, live ISO environment, and reliance on `pacman`, `yay`, and `artix-chroot`.

## Install Flow Basics
- `000-artix-install.sh` runs from the live ISO as root, gathers credentials, installs base packages, and executes an `artix-chroot` heredoc; keep chroot commands non-interactive and idempotent.
- `001-identify-partitions.sh` and `002-setup-partitions.{sh,py}` help map or create labeled partitions; adjust `DESIRED_PARTITIONS` in the Python script instead of hard-coding elsewhere.
- Follow with `010-`/`011-` scripts for mirror setup and package bootstrapping inside the target system; they assume prior creation of `/run/runit/service` symlinks.

## YAML Orchestration (`999-artix-setup.py`)
- Invoked as `python3 999-artix-setup.py <yaml> [--debug]`; debug mode enables verbose logging.
- YAML files such as `021-artix-setup-init.yaml`, `022-artix-setup-*.yaml`, and `024-artix-setup-apps.yaml` drive tasks.
- Supported keys per task: `packages` (with optional `command` override), `shell` (list of commands), `python` (`script` + `parameters`), `file`/`files` (with `content`), and `setup_service` (with `path_init`, `run_file`, `log_file`, `service_init`).
- `service_paths` block supplies placeholders (`service_path`, `sv_path`) used by `setup_service`; keep these consistent across YAML files.

## Package Manifests
- `manifest/*.txt` enumerate packages grouped by role (base, graphics, desktop, apps, gaming).
- `manifest/install_manifest.sh <file>` ensures `yay` exists, refreshes mirrors, strips comments, and runs a single batched `yay -S`; feed clean manifests rather than manual loops.

## Conventions & Tips
- Keep scripts POSIX-compatible when feasible but rely on Bash-specific features already present (arrays, heredocs, brace expansion).
- Prefer extending YAML tasks over editing Python control flow; the orchestrator retries commands, handles sudo, and backs up files when `backup: true` is set.
- When adding services, mirror the `setup_service` structure in `022-artix-setup-*.yaml` and ensure run/log scripts are executable.
- Test risky changes inside a VM or chroot; most scripts mutate system state and lack dry-run flags.
- Use `--debug` logging or temporary `logger.debug` calls in `999-artix-setup.py` for troubleshooting instead of print statements.
