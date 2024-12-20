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
