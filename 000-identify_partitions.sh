#!/bin/bash

# Ensure the script is run as root
if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root."
    exit 1
fi

echo "=== Identifying Partitions ==="

# Detect EFI Partition
EFI_PART=$(lsblk -o NAME,LABEL,FSTYPE,SIZE -nr | grep -i "efi" | awk '$3=="vfat" {print "/dev/" $1}')
if [ -z "$EFI_PART" ]; then
    echo "EFI partition not detected. Please specify manually."
else
    echo "Detected EFI Partition: $EFI_PART"
fi

# Detect Root Partition
ROOT_PART=$(lsblk -o NAME,LABEL,FSTYPE,SIZE -nr | grep -i "ROOT" | awk '$3=="ext4" {print "/dev/" $1}')
if [ -z "$ROOT_PART" ]; then
    echo "Root partition not detected. Please specify manually."
else
    echo "Detected Root Partition: $ROOT_PART"
fi

# Detect Home Partition
HOME_PART=$(lsblk -o NAME,LABEL,FSTYPE,SIZE -nr | grep -i "home" | awk '$3=="ext4" {print "/dev/" $1}')
if [ -z "$HOME_PART" ]; then
    echo "Home partition not detected. Please specify manually."
else
    echo "Detected Home Partition: $HOME_PART"
fi

# Output detected partitions
echo
echo "=== Summary of Detected Partitions ==="
echo "EFI_PART=\"$EFI_PART\""
echo "ROOT_PART=\"$ROOT_PART\""
echo "HOME_PART=\"$HOME_PART\""
