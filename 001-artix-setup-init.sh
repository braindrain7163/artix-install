#!/bin/bash

# Set up download area
mkdir -p ~/source/arch-packages

# Update mirrorlists
sudo cp /etc/pacman.d/mirrorlist /etc/pacman.d/mirrorlist-arch-backup
sudo curl -o /etc/pacman.d/mirrorlist https://gitea.artixlinux.org/packages/artix-mirrorlist/raw/branch/master/mirrorlist

# Download the Arch mirrorlist to a temporary location
curl -o ~/source/arch-packages/mirrorlist-arch https://archlinux.org/mirrorlist/?country=AU&protocol=http&protocol=https&ip_version=4

# Uncomment servers in the downloaded Arch mirrorlist
sed -i 's/^#Server/Server/' ~/source/arch-packages/mirrorlist-arch

# Move the modified Arch mirrorlist to the appropriate location
sudo cp ~/source/arch-packages/mirrorlist-arch /etc/pacman.d/mirrorlist-arch

# Set ownership of the mirrorlists to root
sudo chown root:root /etc/pacman.d/mirrorlist
sudo chown root:root /etc/pacman.d/mirrorlist-arch

# Define the file and tags
file="/etc/pacman.conf"
tags=(
    "[lib32]:Include = /etc/pacman.d/mirrorlist"
    "[extra]:Include = /etc/pacman.d/mirrorlist-arch"
    "[multilib]:Include = /etc/pacman.d/mirrorlist-arch"
)

# Backup the pacman.conf file if not already backed up
if [[ ! -f "$file.bak" ]]; then
  sudo cp "$file" "$file.bak"
elif [[ -f "$file.bak" ]]; then
  sudo cp "$file.bak" "$file"
fi

# Append the tags and their content at the end of the file if not already present
for tag_content in "${tags[@]}"; do
    IFS=":" read -r tag content <<< "$tag_content"
    if ! grep -q "$tag" "$file"; then
        echo -e "\n$tag\n$content" | sudo tee -a "$file" >/dev/null
    else
        echo "$tag already exists in $file"
    fi
done
