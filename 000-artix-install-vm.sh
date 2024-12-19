echo "=== Artix Linux Interactive Installation Script ==="

# Prompt for hostname and username
read -p "Enter hostname (default: artix-host): " HOSTNAME
HOSTNAME=${HOSTNAME:-artix-host}  # Default to 'artix-host' if not provided

read -p "Enter username for new user: " USERNAME
if [ -z "$USERNAME" ]; then
    echo "Username is required."
    exit 1
fi

read -sp "Enter password for root: " ROOT_PASSWORD
echo
read -sp "Enter password for $USERNAME: " USER_PASSWORD
echo

# Prompt for timezone with default
read -p "Enter timezone (default: Australia/Brisbane): " TIMEZONE
TIMEZONE=${TIMEZONE:-Australia/Brisbane}  # Default to 'Australia/Brisbane'

echo "=== Identifying Partitions ==="

# Detect Root Partition
ROOT_PART=$(lsblk -o NAME,FSTYPE,SIZE -nr | grep -i "ext4" | awk '{print "/dev/" $1}')
if [ -z "$ROOT_PART" ]; then
    echo "Root partition not detected. Please specify manually."
    read -p "Enter Root Partition: " ROOT_PART
else
    echo "Detected Root Partition: $ROOT_PART"
    read -p "Enter Root Partition (default: $ROOT_PART): " ROOT_PART_INPUT
    ROOT_PART=${ROOT_PART_INPUT:-$ROOT_PART}
fi

# Output detected partitions
echo
echo "=== Summary of Detected Partitions ==="
echo "ROOT_PART=\"$ROOT_PART\""

# Mount point for installation
MOUNT_POINT="/mnt"

# Step 1: Confirm Formatting Root Partition
echo "Step 1: Format the root partition ($ROOT_PART)."
read -p "Do you want to format the root partition? (y/n): " CONFIRM
if [[ "$CONFIRM" =~ ^[Yy]$ ]]; then
    mkfs.ext4 -L root $ROOT_PART
    echo "Root partition formatted."
else
    echo "Skipping root partition formatting."
fi

# Step 2: Confirm Mounting Partitions
echo "Step 2: Mount partitions."
read -p "Do you want to mount the partitions? (y/n): " CONFIRM
if [[ "$CONFIRM" =~ ^[Yy]$ ]]; then
    mount $ROOT_PART $MOUNT_POINT
    echo "Partitions mounted."
else
    echo "Skipping partition mounting."
fi

# Step 3: Confirm Installing Base System
echo "Step 3: Install the base system."
read -p "Do you want to install the base system? (y/n): " CONFIRM
if [[ "$CONFIRM" =~ ^[Yy]$ ]]; then
    basestrap $MOUNT_POINT base base-devel runit elogind-runit linux linux-firmware nano intel-ucode git vi man-db htop neovim sudo
    echo "Base system installed."
else
    echo "Skipping base system installation."
fi

# Step 4: Confirm Generating fstab
echo "Step 4: Generate fstab."
read -p "Do you want to generate the fstab file? (y/n): " CONFIRM
if [[ "$CONFIRM" =~ ^[Yy]$ ]]; then
    if command -v fstabgen &> /dev/null; then
        fstabgen -U $MOUNT_POINT > /tmp/fstab
    elif command -v genfstab &> /dev/null; then
        genfstab -U $MOUNT_POINT > /tmp/fstab
    else
        echo "fstabgen or genfstab not found!"
        exit 1
    fi
    mv /tmp/fstab $MOUNT_POINT/etc/fstab
    echo "fstab file generated:"
    cat $MOUNT_POINT/etc/fstab
else
    echo "Skipping fstab generation."
fi
