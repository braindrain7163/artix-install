#!/bin/bash

# Install package
echo "Installing input-remapper..."
yay -S input-remapper-bin --noconfirm

# Create the dinit directories if they don't exist
sudo mkdir -p /etc/dinit.d
sudo mkdir -p /etc/dinit.d/boot.d

# Create service file with error handling
if [ -f "/etc/dinit.d/input-remapper" ]; then
    echo "Service file already exists, backing up..."
    sudo mv "/etc/dinit.d/input-remapper" "/etc/dinit.d/input-remapper.bak"
fi

# Create the service file
sudo tee "/etc/dinit.d/input-remapper" << 'EOF' > /dev/null
# input-remapper Dinit service
type=process
name=input-remapper
exec=/usr/bin/input-remapper-gtk
user=root
group=input
depends-on=display-manager
smooth-recovery = true
restart=restart
logfile=/var/log/input-remapper.log

EOF

# Handle symlink creation
if [ -L "/etc/dinit.d/boot.d/input-remapper" ]; then
    echo "Boot symlink already exists, removing..."
    sudo rm "/etc/dinit.d/boot.d/input-remapper"
fi

# Create new symlink
sudo ln -s "../input-remapper" "/etc/dinit.d/boot.d/input-remapper"

# Start the service
sudo dinitctl start input-remapper

echo "Input-remapper service setup complete" 