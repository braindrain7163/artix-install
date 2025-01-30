#!/bin/bash

# Mount point for installation
MOUNT_POINT="/mnt"

# Ensure the script is run as root
if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root."
    exit 1
fi

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

# # Run partition setup script
# PARTITION_SCRIPT="./002-setup-partitions.sh"
# if [ -x "$PARTITION_SCRIPT" ]; then
#     echo "Running partition setup script: $PARTITION_SCRIPT"
#     "$PARTITION_SCRIPT"
# else
#     echo "Error: Partition setup script not found or not executable: $PARTITION_SCRIPT"
#     exit 1
# fi


# Step 1: Confirm Installing Base System
echo "Step 1: Install the base system."
read -p "Do you want to install the base system? (y/n): " CONFIRM
if [[ "$CONFIRM" =~ ^[Yy]$ ]]; then
    basestrap $MOUNT_POINT base base-devel runit elogind-runit linux linux-firmware nano intel-ucode git vi man-db neovim sudo networkmanager networkmanager-runit
    echo "Base system installed."
else
    echo "Skipping base system installation."
fi

# Step 2: Confirm Generating fstab
echo "Step 2: Generate fstab."
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

# Step 3: Confirm Entering Chroot
echo "Step 3: Chroot into the new system."
read -p "Do you want to chroot into the new system? (y/n "$MOUNT_POINT": " CONFIRM
if [[ "$CONFIRM" =~ ^[Yy]$ ]]; then
    artix-chroot $MOUNT_POINT /bin/bash << EOT

    # Inside chroot: Configure system
    echo "Configuring system inside chroot..."

    # Setup services directories
    mkdir -p /run/runit/
    ln -s /etc/runit/runsvdir/current /run/runit/service
    
    # Set timezone
    ln -sf /usr/share/zoneinfo/$TIMEZONE /etc/localtime
    hwclock --systohc

    # Set hostname
    echo "$HOSTNAME" > /etc/hostname

    # Configure /etc/hosts
    cat << EOF > /etc/hosts
127.0.0.1   localhost
::1         localhost
127.0.1.1   $HOSTNAME.localdomain $HOSTNAME
EOF
    
    # Set root password
    echo "Set root password:"
    echo "root:$ROOT_PASSWORD" | chpasswd

    # Create a new user
    useradd -m -G wheel -s /bin/bash "$USERNAME"
    echo "Set password for $USERNAME:"
    echo "$USERNAME:$USER_PASSWORD" | chpasswd
    usermod -a -G wheel "$USERNAME"

    # Allow sudo for the new user
    pacman -S sudo --noconfirm
    echo "%wheel ALL=(ALL "$MOUNT_POINT" ALL" >> /etc/sudoers

    # Install and configure GRUB
    pacman -S grub os-prober efibootmgr --noconfirm
    grub-install --target=x86_64-efi --efi-directory=/boot/efi --bootloader-id=GRUB
    os-prober
    grub-mkconfig -o /boot/grub/grub.cfg

EOT
    echo "Exiting chroot."
else
    echo "Skipping chroot."
fi

# Post-installation instructions
echo "1. To log back in:"
echo "   artix-chroot $MOUNT_POINT /bin/bash"

echo "Installation complete. Reboot into your new system when ready."
