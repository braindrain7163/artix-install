echo "=== Identifying Partitions ==="

# Detect EFI Partition
EFI_PART=$(lsblk -o NAME,LABEL,FSTYPE,SIZE -nr | grep -i "efi" | awk '$3=="vfat" && $1 !~ /^sd[a-z]/ {print "/dev/" $1}' | head -n 1)
if [ -z "$EFI_PART" ]; then
    echo "EFI partition not detected. Please specify manually."
else
    echo "Detected EFI Partition: $EFI_PART"
fi

# Detect Root Partition
ROOT_PART=$(lsblk -o NAME,LABEL,FSTYPE,SIZE -nr | grep -i "ROOT" | awk '$3=="ext4" && $1 !~ /^sd[a-z]/ {print "/dev/" $1}' | head -n 1)
if [ -z "$ROOT_PART" ]; then
    echo "Root partition not detected. Please specify manually."
else
    echo "Detected Root Partition: $ROOT_PART"
fi

# Detect Home Partition
HOME_PART=$(lsblk -o NAME,LABEL,FSTYPE,SIZE -nr | grep -i "home" | awk '$3=="ext4" && $1 !~ /^sd[a-z]/ {print "/dev/" $1}' | head -n 1)
if [ -z "$HOME_PART" ]; then
    echo "Home partition not detected. Please specify manually."
else
    echo "Detected Home Partition: $HOME_PART"
fi

# Output detected partitions
echo
echo "=== Summary of Detected Partitions ==="
echo "EFI_PART=\"$EFI_PART\""
echo "ROOT_PART=\"$ROOT_PART\""
echo "HOME_PART=\"$HOME_PART\""

# Detect EFI Partition
EFI_PART=$(lsblk -o NAME,LABEL,FSTYPE,SIZE -nr | grep -i "efi" | awk '$3=="vfat" && $1 !~ /^sd[a-z]/ {print "/dev/" $1}' | head -n 1)
if [ -z "$EFI_PART" ]; then
    echo "EFI partition not detected. Please specify manually."
    read -p "Enter EFI Partition: " EFI_PART
else
    echo "Detected EFI Partition: $EFI_PART"
    read -p "Enter EFI Partition (default: $EFI_PART): " EFI_PART_INPUT
    EFI_PART=${EFI_PART_INPUT:-$EFI_PART}
fi

# Detect Root Partition
ROOT_PART=$(lsblk -o NAME,LABEL,FSTYPE,SIZE -nr | grep -i "ROOT" | awk '$3=="ext4" && $1 !~ /^sd[a-z]/ {print "/dev/" $1}' | head -n 1)
if [ -z "$ROOT_PART" ]; then
    echo "Root partition not detected. Please specify manually."
    read -p "Enter Root Partition: " ROOT_PART
else
    echo "Detected Root Partition: $ROOT_PART"
    read -p "Enter Root Partition (default: $ROOT_PART): " ROOT_PART_INPUT
    ROOT_PART=${ROOT_PART_INPUT:-$ROOT_PART}
fi

# Detect Home Partition
HOME_PART=$(lsblk -o NAME,LABEL,FSTYPE,SIZE -nr | grep -i "home" | awk '$3=="ext4" && $1 !~ /^sd[a-z]/ {print "/dev/" $1}' | head -n 1)
if [ -z "$HOME_PART" ]; then
    echo "Home partition not detected. Please specify manually."
    read -p "Enter Home Partition: " HOME_PART
else
    echo "Detected Home Partition: $HOME_PART"
    read -p "Enter Home Partition (default: $HOME_PART): " HOME_PART_INPUT
    HOME_PART=${HOME_PART_INPUT:-$HOME_PART}
fi

# Output detected partitions
echo
echo "=== Summary of Detected Partitions ==="
echo "EFI_PART=\"$EFI_PART\""
echo "ROOT_PART=\"$ROOT_PART\""
echo "HOME_PART=\"$HOME_PART\""
