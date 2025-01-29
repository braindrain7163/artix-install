#!/bin/bash

set -e

# Accept the mount point as the first argument
MOUNT_POINT="$1"
if [ -z "$MOUNT_POINT" ]; then
    echo "Error: No mount point provided."
    exit 1
fi

# Define the required partitions, sizes, and those to format
PARTITIONS=("root" "opt" "var" "home" "swap")
FORMAT_PARTITIONS=("opt" "var")
PARTITION_SIZES=("128G" "128G" "355G" "" "64G")

# Prompt for disks
echo "Available disks:"
lsblk -d -o NAME,SIZE | grep -v "loop" | grep -v "rom"

read -p "Enter the disk to use for system partitions (root, opt, var, swap): " SYSTEM_DISK
if [ -z "$SYSTEM_DISK" ]; then
    echo "Error: No disk selected for system partitions."
    exit 1
fi

read -p "Enter the disk to use for the home partition: " HOME_DISK
if [ -z "$HOME_DISK" ]; then
    echo "Error: No disk selected for the home partition."
    exit 1
fi

# Check for partitions and assign them
for i in "${!PARTITIONS[@]}"; do
    PARTITION_LABEL="${PARTITIONS[$i]}"
    PARTITION_SIZE="${PARTITION_SIZES[$i]}"

    PARTITION=$(lsblk -o LABEL,NAME -nr | grep "^$PARTITION_LABEL" | awk '{print $2}')

    if [ -z "$PARTITION" ]; then
        echo "Partition with label $PARTITION_LABEL not found."
        read -p "Do you want to create the $PARTITION_LABEL partition (size: $PARTITION_SIZE)? [y/N]: " CREATE_PARTITION
        if [[ "$CREATE_PARTITION" =~ ^[Yy]$ ]]; then
            echo "Creating $PARTITION_LABEL partition..."

            # Determine which disk to use
            if [ "$PARTITION_LABEL" == "home" ]; then
                DISK="$HOME_DISK"
            else
                DISK="$SYSTEM_DISK"
            fi

            echo "Using disk: /dev/$DISK"

            # Create the partition
            if [ "$PARTITION_LABEL" == "swap" ]; then
                sudo parted /dev/$DISK mkpart primary linux-swap 0% $PARTITION_SIZE
            else
                sudo parted /dev/$DISK mkpart primary ext4 0% $PARTITION_SIZE
            fi
            sudo parted /dev/$DISK name $((i + 1)) $PARTITION_LABEL
            sudo partprobe /dev/$DISK

            PARTITION=$(lsblk -o LABEL,NAME -nr | grep "^$PARTITION_LABEL" | awk '{print $2}')

            if [ -z "$PARTITION" ]; then
                echo "Error: Failed to create partition $PARTITION_LABEL."
                exit 1
            fi

            echo "Partition $PARTITION_LABEL created: /dev/$PARTITION"
        else
            echo "Skipping creation of $PARTITION_LABEL."
            continue
        fi
    fi

    echo "Partition for $PARTITION_LABEL found: /dev/$PARTITION"

    # Assign partitions to variables
    case $PARTITION_LABEL in
        root)
            ROOT_PARTITION="/dev/$PARTITION"
            ;;
        opt)
            OPT_PARTITION="/dev/$PARTITION"
            ;;
        var)
            VAR_PARTITION="/dev/$PARTITION"
            ;;
        home)
            HOME_PARTITION="/dev/$PARTITION"
            ;;
        swap)
            SWAP_PARTITION="/dev/$PARTITION"
            ;;
    esac
done

# Prompt to format each system partition except root and swap
for PARTITION_LABEL in "${FORMAT_PARTITIONS[@]}"; do
    PARTITION_VAR="${PARTITION_LABEL^^}_PARTITION"
    PARTITION_DEVICE="${!PARTITION_VAR}"

    if [ -n "$PARTITION_DEVICE" ]; then
        read -p "Do you want to format the $PARTITION_LABEL partition ($PARTITION_DEVICE)? [y/N]: " FORMAT_PARTITION
        if [[ "$FORMAT_PARTITION" =~ ^[Yy]$ ]]; then
            echo "Formatting $PARTITION_LABEL partition: $PARTITION_DEVICE"
            mkfs.ext4 -F "$PARTITION_DEVICE"
        else
            echo "Skipping formatting of $PARTITION_LABEL partition."
        fi
    else
        echo "Error: Device for $PARTITION_LABEL not found."
        exit 1
    fi
done

# Set up swap
if [ -n "$SWAP_PARTITION" ]; then
    echo "Setting up swap partition: $SWAP_PARTITION"
    mkswap "$SWAP_PARTITION"
    swapon "$SWAP_PARTITION"
fi

# Mount partitions
mount "$ROOT_PARTITION" "$MOUNT_POINT"
mkdir -p "$MOUNT_POINT"/{opt,var,home}
mount "$OPT_PARTITION" "$MOUNT_POINT/opt"
mount "$VAR_PARTITION" "$MOUNT_POINT/var"
mount "$HOME_PARTITION" "$MOUNT_POINT/home"

echo "Partition setup complete."
