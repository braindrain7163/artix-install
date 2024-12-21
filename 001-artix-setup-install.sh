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
sudo pacman -S curl git base-devel --noconfirm

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

#fix grub
sudo pacman -S grub os-prober --noconfirm
sudo os-prober
sudo grub-mkconfig -o /boot/grub/grub.cfg

#setup services
sudo mkdir /run/runit/service -P

# Link acpid service
if [[ ! -L /run/runit/service/acpid ]]; then
  sudo ln -s /etc/runit/sv/acpid /run/runit/service/
  echo "Created symlink: /run/runit/service/acpid"
else
  echo "Symlink already exists: /run/runit/service/acpid"
fi

if [[ ! -L /etc/runit/runsvdir/default/acpid ]]; then
  sudo ln -s /etc/runit/sv/acpid /etc/runit/runsvdir/default
  echo "Created symlink: /etc/runit/runsvdir/default/acpid"
else
  echo "Symlink already exists: /etc/runit/runsvdir/default/acpid"
fi

# Link NetworkManager service
if [[ ! -L /run/runit/service/NetworkManager ]]; then
  sudo ln -s /etc/runit/sv/NetworkManager /run/runit/service/
  echo "Created symlink: /run/runit/service/NetworkManager"
else
  echo "Symlink already exists: /run/runit/service/NetworkManager"
fi

if [[ ! -L /etc/runit/runsvdir/default/NetworkManager ]]; then
  sudo ln -s /etc/runit/sv/NetworkManager /etc/runit/runsvdir/default
  echo "Created symlink: /etc/runit/runsvdir/default/NetworkManager"
else
  echo "Symlink already exists: /etc/runit/runsvdir/default/NetworkManager"
fi
