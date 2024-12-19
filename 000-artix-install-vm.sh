#!/bin/bash
# Artix Linux VM installation script

# Update system
sudo pacman -Syu

# Install base packages
sudo pacman -S base base-devel linux linux-firmware

# Install additional packages
sudo pacman -S grub efibootmgr nano networkmanager dhcpcd

# Partition the disk
# Automatically identify the disk (assuming only one disk is attached)
disk=$(lsblk -dn -o NAME,TYPE | awk '$2=="disk" {print "/dev/"$1}')
echo "Target disk: $disk"

# Wipe the disk
sudo wipefs -a $disk
sudo sgdisk --zap-all $disk

# Create partitions
sudo parted $disk -- mklabel gpt
sudo parted $disk -- mkpart ESP fat32 1MiB 512MiB
sudo parted $disk -- set 1 boot on
sudo parted $disk -- mkpart primary ext4 512MiB 100%

# Format partitions
sudo mkfs.fat -F32 ${disk}1
sudo mkfs.ext4 ${disk}2

# Mount partitions
sudo mount ${disk}2 /mnt
sudo mkdir -p /mnt/boot
sudo mount ${disk}1 /mnt/boot

# Install the base system
sudo pacstrap /mnt base base-devel linux linux-firmware

# Generate an fstab file
sudo genfstab -U /mnt >> /mnt/etc/fstab

# Chroot into the installed system
arch-chroot /mnt <<EOF

# Set the time zone
ln -sf /usr/share/zoneinfo/Region/City /etc/localtime
hwclock --systohc

# Configure the locale
echo "en_US.UTF-8 UTF-8" > /etc/locale.gen
locale-gen
echo "LANG=en_US.UTF-8" > /etc/locale.conf

# Configure the hostname
echo "artix-vm" > /etc/hostname
echo -e "127.0.0.1\tlocalhost" >> /etc/hosts
echo -e "::1\tlocalhost" >> /etc/hosts
echo -e "127.0.1.1\tartix-vm.localdomain artix-vm" >> /etc/hosts

# Set the root password
passwd

# Install and configure GRUB
grub-install --target=x86_64-efi --efi-directory=/boot --bootloader-id=GRUB
grub-mkconfig -o /boot/grub/grub.cfg

# Enable essential services
ln -s /etc/runit/sv/NetworkManager /etc/runit/runsvdir/default/

EOF

# Unmount partitions
# sudo umount -R /mnt

# Installation complete
echo "Artix Linux installation complete. You can now reboot."


# Post-installation instructions
echo "1. to log back in:"
echo "   artix-chroot $MOUNT_POINT /bin/bash"
echo "2. EDITOR=nano visudo"
echo "3. Find Wheel Group"
echo "4. Uncomment %wheel ALL=(All) ALL"
echo "7. Reboot the system."

#https://github.com/Zerogaku/Artix-install-guide

echo "Installation complete. Reboot into your new system when ready and check https://github.com/Zerogaku/Artix-install-guide for some more hints"
