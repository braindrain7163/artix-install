#!/bin/bash

# Function to check if yay is installed
function is_yay_installed {
  command -v yay >/dev/null 2>&1
}

# Update and populate keyrings
sudo pacman -Sy gnupg archlinux-keyring artix-keyring --noconfirm
sudo pacman-key --populate archlinux artix

# Full system upgrade
sudo pacman -Syuu --noconfirm

#addbuild stuff
sudo pacman -S curl git base-devel artix-archlinux-support  archlinux-mirrorlist --noconfirm

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
sudo pacman -S world/python --noconfirm
sudo pacman -S world/python-yaml --noconfirm

#fix grub
sudo pacman -S grub os-prober --noconfirm
sudo os-prober
sudo grub-mkconfig -o /boot/grub/grub.cfg
