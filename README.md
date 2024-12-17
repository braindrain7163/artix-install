# Artix Install

A collection of scripts and documentation for automating and simplifying the installation process of **Artix Linux**.

## Table of Contents

- [Introduction](#introduction)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Scripts Overview](#scripts-overview)
- [Customization](#customization)
- [Contributing](#contributing)
- [License](#license)

---

## Introduction

Artix Install is designed to streamline the process of installing **Artix Linux**, a systemd-free distribution. These scripts automate common setup tasks, including system initialization, partitioning, bootloader installation, and configuration of key system components.

---

## Features

- **Base System Initialization:** Prepares the environment for installation.
- **Automated Partitioning:** Easily set up partitions with minimal input.
- **Bootloader Installation:** Automatically installs GRUB or other supported bootloaders.
- **Network Configuration:** Set up Wi-Fi, Ethernet, and other networking tools.
- **Customizable Scripts:** Adjust to meet specific installation needs.

---

## Requirements

- **Artix Linux ISO** (download from [artixlinux.org](https://artixlinux.org))
- **Internet Connection**
- **A Blank Hard Drive or Partition**
- **USB Drive** for bootable media creation

**Tools Needed:**
- `bash`
- `pacman` (package manager for Artix Linux)
- `parted` or `fdisk` for disk management

---

## Installation

### Step 1: Boot into the Artix Linux Live ISO

1. Boot from the **Artix Linux ISO**.
2. Clone the repository to your live environment:

   ```bash
   git clone https://github.com/braindrain7163/artix-install.git
   cd artix-install
   ```

3. Make the scripts executable:

   ```bash
   chmod +x *.sh
   ```

4. Run the **main install** script (must run from the ISO environment):

   ```bash
   ./000-artix-install.sh
   ```

   This script handles disk partitioning, base system installation, and bootloader setup.

### Step 2: Reboot and Run Setup Initialization

1. Once the installation is complete, reboot into the newly installed system.
2. Log in and run the **setup initialization** script:

   ```bash
   ./001-artix-setup-init.sh
   ```

   This script configures system settings, networking, and mirrors.

---

## Usage

- **000-artix-install.sh** (Run from ISO): Handles the full installation process, including partitioning, base system installation, and bootloader setup.
- **001-artix-setup-init.sh** (Run after reboot): Configures system settings such as time zones, mirrors, and networking.

Run these scripts in order:

1. From the ISO:
   ```bash
   ./000-artix-install.sh
   ```
2. After rebooting into the new system:
   ```bash
   ./001-artix-setup-init.sh
   ```

---

## Scripts Overview

- **`000-artix-install.sh`** - Main installation script (to run from ISO):
  - Handles partitioning.
  - Installs the base system.
  - Configures GRUB bootloader.
- **`001-artix-setup-init.sh`** - Post-installation setup script (to run after reboot):
  - Updates system time.
  - Configures mirrors.
  - Sets up networking.

---

## Customization

You can customize any script to suit your requirements:

- Modify `000-artix-install.sh` for specific partition layouts or packages.
- Adjust `001-artix-setup-init.sh` for custom networking or post-install configurations.

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository.
2. Create a new branch:
   ```bash
   git checkout -b feature/new-feature
   ```
3. Make changes and commit:
   ```bash
   git commit -m "Add new feature"
   ```
4. Push and open a pull request.

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Acknowledgments

Thanks to the Artix Linux community for creating a great systemd-free Linux distribution.
