#!/bin/bash

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

echo "=== Identifying Partitions ==="

# Partition the disk
# Automatically identify the disk (assuming only one disk is attached)
disk=$(lsblk -dn -o NAME,TYPE | awk '$2=="disk" {print "/dev/"$1}')
echo "Target disk: $disk"

# Create MBR partition table and partitions
sudo parted $disk -- mklabel msdos
sudo parted $disk -- mkpart primary ext4 1MiB 100%
sudo parted $disk -- set 1 boot on

# Format the partition
sudo mkfs.ext4 ${disk}1

# Set the mount point
MOUNT_POINT="/mnt"
sudo mkdir -p $MOUNT_POINT

# Mount the partition
sudo mount ${disk}1 $MOUNT_POINT

#Installing Base System
echo "Install the base system."
read -p "Do you want to install the base system? (y/n): " CONFIRM
if [[ "$CONFIRM" =~ ^[Yy]$ ]]; then
    basestrap $MOUNT_POINT base base-devel runit elogind-runit linux linux-firmware nano intel-ucode git vi man-db htop neovim sudo
    echo "Base system installed."
else
    echo "Skipping base system installation."
fi

#Confirm Generating fstab
echo "Generate fstab."
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
    sudo mv /tmp/fstab $MOUNT_POINT/etc/fstab
    echo "fstab file generated:"
    cat $MOUNT_POINT/etc/fstab
else
    echo "Skipping fstab generation."
fi

#Confirm Entering Chroot
echo "Chroot into the new system."
read -p "Do you want to chroot into the new system? (y/n): " CONFIRM
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
    echo "%wheel ALL=(ALL) ALL" >> /etc/sudoers

    # connman-gtk
    # pacman -U https://omniverse.artixlinux.org/x86_64/connman-gtk-1.1.1-3-x86_64.pkg.tar.zst --noconfirm
    # pacman -S artix-keyring archlinux-keyring --noconfirm
    # pacman-key --populate artix
    # pacman-key --populate archlinux
    # pacman -S connman-runit --noconfirm
    # # ln -s /etc/runit/sv/connmand /run/runit/service/    
    # ln -s /etc/runit/sv/connmand /etc/runit/runsvdir/default

    #network setup
    pacman -S networkmanager networkmanager-runit network-manager-applet --noconfirm
    # pacman -S dhcpcd --noconfirm
    ln -s /etc/runit/sv/NetworkManager /run/runit/service/

    #basic system
    pacman -S xdg-utils xdg-user-dirs python --noconfirm
    pacman -S xf86-video-qxl spice-vdagent mesa --noconfirm

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
echo "1. to log back in:"
echo "   artix-chroot $MOUNT_POINT /bin/bash"
echo "2. EDITOR=nano visudo"
echo "3. Find Wheel Group"
echo "4. Uncomment %wheel ALL=(All) ALL"
echo "5. Check Connection Manager is setup"
echo "   ln -s /etc/runit/sv/connmand /etc/runit/runsvdir/default"
echo "6. Reboot the system."

echo "Check these resrouces for assistance"
echo "https://github.com/Zerogaku/Artix-install-guide/"
echo "https://cheatsheets.stephane.plus/distros/arch-based/artix_installation/"

echo "Installation complete. Reboot into your new system when ready and check https://github.com/Zerogaku/Artix-install-guide for some more hints"
