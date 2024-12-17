#!/bin/bash

# Function to check if yay is installed
function is_yay_installed {
  command -v yay >/dev/null 2>&1
}

# Update mirrorlists
sudo curl -o /etc/pacman.d/mirrorlist https://gitea.artixlinux.org/packages/artix-mirrorlist/raw/branch/master/mirrorlist
sudo curl -o /etc/pacman.d/mirrorlist-arch https://archlinux.org/mirrorlist/?country=AU&protocol=http&protocol=https&ip_version=4


sudo sed -i 's/^#Server/Server/' /etc/pacman.d/mirrorlist-arch

# Define the file and tags
file="/etc/pacman.conf"
tags=(
    "[lib32]:Include = /etc/pacman.d/mirrorlist"
    "[extra]:Include = /etc/pacman.d/mirrorlist-arch"
    "[multilib]:Include = /etc/pacman.d/mirrorlist-arch"
)

# Append the tags and their content at the end of the file
for tag_content in "${tags[@]}"; do
    IFS=":" read -r tag content <<< "$tag_content"
    echo -e "\n$tag\n$content" >> "$file"
done

# Update and populate keyrings
sudo pacman -Sy gnupg archlinux-keyring artix-keyring --noconfirm
sudo pacman-key --populate archlinux artix

# Full system upgrade
sudo pacman -Syuu --noconfirm

#addbuild stuff
sudo pacman -S curl git base-devel --noconfirm

# Set up yay (AUR Helper)
mkdir -p ~/source/arch-packages

if ! is_yay_installed; then
  echo "yay not found, proceeding to build..."

  cd ~/source/arch-packages

  if [ ! -d "yay" ]; then
    git clone https://aur.archlinux.org/yay.git
  else
    cd ~/source/arch-packages/yay
    git pull || exit 1
  fi

  cd ~/source/arch-packages/yay
  makepkg -si --noconfirm
else
  echo "yay is already installed, checking for updates..."

  if [ -d "~/source/arch-packages/yay" ]; then
    cd ~/source/arch-packages/yay
    git fetch
    LOCAL=$(git rev-parse HEAD)
    REMOTE=$(git rev-parse @{u})

    if [ "$LOCAL" != "$REMOTE" ]; then
      echo "yay source has changed, rebuilding..."
      git pull
      makepkg -si --noconfirm
    else
      echo "yay is up-to-date, skipping rebuild."
    fi
  else
    echo "/git/yay does not exist. Please check your setup."
    exit 1
  fi
fi

# Install PyYAML
sudo pacman -S world/python-yaml --noconfirm

#install larbs
cd ~/source/arch-packages
curl -LO larbs.xyz/larbs.sh
echo "to install larbs run: sh larbs.sh"

#fix grub
sudo pacman -S grub os-prober --noconfirm
sudo os-prober
sudo grub-mkconfig -o /boot/grub/grub.cfg

#setup services
sudo mkdir /run/runit/service -P
sudo ln -s /etc/runit/sv/connmand /run/runit/service/    
sudo ln -s /etc/runit/sv/connmand /etc/runit/runsvdir/default
# ln -s /etc/runit/sv/NetworkManager /run/runit/service/

sudo ln -s /etc/runit/sv/dhcpcd /run/runit/service/
sudo ln -s /etc/runit/sv/dhcpcd /etc/runit/runsvdir/default

sudo ln -s /etc/runit/sv/bluetoothd /run/runit/service/
sudo ln -s /etc/runit/sv/bluetoothd /etc/runit/runsvdir/default

sudo ln -s /etc/runit/sv/cupsd /run/runit/service/
sudo ln -s /etc/runit/sv/cupsd /etc/runit/runsvdir/default

sudo ln -s /etc/runit/sv/acpid /run/runit/service/
sudo ln -s /etc/runit/sv/acpid /etc/runit/runsvdir/default

