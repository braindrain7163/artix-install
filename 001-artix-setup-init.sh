#!/bin/bash

# Variables
DOWNLOAD_DIR=~/source/arch-packages
ARTIX_MIRRORLIST="/etc/pacman.d/mirrorlist"
ARTIX_MIRRORLIST_BACKUP="/etc/pacman.d/mirrorlist-arch-backup"
ARCH_MIRRORLIST="$DOWNLOAD_DIR/mirrorlist-arch"
ARCH_MIRRORLIST_DEST="/etc/pacman.d/mirrorlist-arch"

# Set up download area
mkdir -p "$DOWNLOAD_DIR"

# Update Artix mirrorlist
echo "Backing up Artix mirrorlist to $ARTIX_MIRRORLIST_BACKUP..."
sudo cp "$ARTIX_MIRRORLIST" "$ARTIX_MIRRORLIST_BACKUP"
if sudo curl -o "$ARTIX_MIRRORLIST" https://gitea.artixlinux.org/packages/artix-mirrorlist/raw/branch/master/mirrorlist; then
  echo "Artix mirrorlist updated successfully."
else
  echo "Failed to update Artix mirrorlist." >&2
  exit 1
fi

# Download the Arch Linux mirrorlist
echo "Downloading Arch Linux mirrorlist to $ARCH_MIRRORLIST..."
if curl -o "$ARCH_MIRRORLIST" "https://archlinux.org/mirrorlist/?country=AU"; then
  echo "Successfully downloaded Arch Linux mirrorlist."
else
  echo "Failed to download Arch Linux mirrorlist. Trying alternative URL..." >&2
  if curl -o "$ARCH_MIRRORLIST" "https://archlinux.org/mirrorlist/all/"; then
    echo "Successfully downloaded Arch Linux mirrorlist from the alternative URL."
  else
    echo "Failed to download Arch Linux mirrorlist from all sources." >&2
    exit 1
  fi
fi

# Uncomment servers in the downloaded Arch mirrorlist
echo "Uncommenting servers in the Arch Linux mirrorlist..."
if sed -i 's/^#Server/Server/' "$ARCH_MIRRORLIST"; then
  echo "Servers uncommented successfully in $ARCH_MIRRORLIST."
else
  echo "Failed to uncomment servers in the Arch Linux mirrorlist." >&2
  exit 1
fi

# Move the modified Arch mirrorlist to the appropriate location
echo "Moving the Arch Linux mirrorlist to $ARCH_MIRRORLIST_DEST..."
if sudo cp "$ARCH_MIRRORLIST" "$ARCH_MIRRORLIST_DEST"; then
  echo "Arch Linux mirrorlist moved successfully."
else
  echo "Failed to move Arch Linux mirrorlist to $ARCH_MIRRORLIST_DEST." >&2
  exit 1
fi

# Set ownership of the mirrorlists to root
echo "Setting ownership of mirrorlists to root..."
if sudo chown root:root "$ARTIX_MIRRORLIST" && sudo chown root:root "$ARCH_MIRRORLIST_DEST"; then
  echo "Ownership of mirrorlists set successfully."
else
  echo "Failed to set ownership of the mirrorlists." >&2
  exit 1
fi

echo "Mirrorlist update completed successfully!"

#!/bin/bash

# Define the file and tags
path="/etc"
file="pacman.conf"
DOWNLOAD_DIR=~/source/arch-packages
TAGS=(
    "[lib32]:Include = /etc/pacman.d/mirrorlist"
    "[extra]:Include = /etc/pacman.d/mirrorlist-arch"
    "[multilib]:Include = /etc/pacman.d/mirrorlist-arch"
    "[community]:Include = /etc/pacman.d/mirrorlist-arch"
)

# Ensure the download directory exists
mkdir -p "$DOWNLOAD_DIR"

# Backup the pacman.conf file if not already backed up
PACMAN_CONF_BACKUP="$DOWNLOAD_DIR/$file.bak"
if [[ ! -f "$PACMAN_CONF_BACKUP" ]]; then
  echo "Backing up $path/$file to $PACMAN_CONF_BACKUP..."
  sudo cp "$path/$file" "$PACMAN_CONF_BACKUP"
else
  echo "Backup already exists at $PACMAN_CONF_BACKUP."
fi

# Append the tags to the backup file
echo "Appending tags to the backup file..."
for tag_content in "${TAGS[@]}"; do
  # Extract the tag and content
  tag="${tag_content%%:*}"
  content="${tag_content#*:}"

  echo -e "\n$tag\n$content" | sudo tee -a "$PACMAN_CONF_BACKUP" >/dev/null
  echo "Added $tag to the backup file."
done

# Replace the original pacman.conf with the modified backup
echo "Replacing $path/$file with the updated backup..."
if sudo cp "$PACMAN_CONF_BACKUP" "$path/$file"; then
  echo "$file updated successfully."
else
  echo "Failed to update $file." >&2
  exit 1
fi
