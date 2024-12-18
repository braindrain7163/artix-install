#!/bin/bash

echo "=== Identifying Drives ==="

# List available drives
lsblk -o NAME,SIZE,TYPE | grep -w "disk"
echo
echo "Available drives:"
lsblk -d -o NAME,SIZE,MODEL

# Prompt user to select a drive
echo
read -p "Enter the drive name (e.g., sda) where you want to create partitions: " DRIVE
DRIVE="/dev/$DRIVE"

# Verify the selected drive
if [ ! -b "$DRIVE" ]; then
    echo "Error: Drive $DRIVE not found!"
    exit 1
fi

# Check for existing partitions
echo
echo "=== Checking Partitions on $DRIVE ==="
lsblk "$DRIVE" -o NAME,LABEL,FSTYPE,SIZE
PART_COUNT=$(lsblk -nr "$DRIVE" | wc -l)

if [ "$PART_COUNT" -gt 1 ]; then
    echo "Partitions detected on $DRIVE."
    echo "If you proceed, existing data may be overwritten."
    read -p "Do you want to proceed with partitioning? (yes/no): " CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        echo "Exiting."
        exit 1
    fi
fi

# Create EFI Partition
echo
echo "=== Creating EFI Partition ==="
EFI_SIZE="512MiB"
echo "Creating a 512 MiB EFI partition on $DRIVE..."
parted --script "$DRIVE" mklabel gpt
parted --script "$DRIVE" mkpart primary fat32 1MiB "$EFI_SIZE"
parted --script "$DRIVE" set 1 boot on

# Assign EFI Partition
if [[ "$DRIVE" == *"nvme"* ]]; then
    EFI_PART="${DRIVE}p1"
else
    EFI_PART="${DRIVE}1"
fi
echo "Created EFI Partition: $EFI_PART"
mkfs.vfat -F32 -n efi "$EFI_PART"

# Create Root Partition
echo
echo "=== Creating Root Partition ==="
ROOT_SIZE="512GiB"
ROOT_START="$EFI_SIZE"
echo "Creating a root partition of size $ROOT_SIZE on $DRIVE..."
parted --script "$DRIVE" mkpart primary ext4 "$ROOT_START" "$ROOT_SIZE"

# Assign Root Partition
if [[ "$DRIVE" == *"nvme"* ]]; then
    ROOT_PART="${DRIVE}p2"
else
    ROOT_PART="${DRIVE}2"
fi
echo "Created Root Partition: $ROOT_PART"
mkfs.ext4 -L root "$ROOT_PART"

# Output Summary
echo
echo "=== Summary of Created Partitions ==="
echo "EFI_PART=\"$EFI_PART\" (Label: EFI, Size: 512 MiB)"
echo "ROOT_PART=\"$ROOT_PART\" (Label: root, Size: 512 GiB)"
echo "Partitions have been successfully created and formatted."
