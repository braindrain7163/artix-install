#!/usr/bin/env python3

import os
import re
import subprocess
import sys

##############################################################################
# STEP 1: Define desired partition labels and their configuration
##############################################################################

DESIRED_PARTITIONS = {
    "EFI": {
        "size":  "512MiB",
        "type":  "fat32",
        "format": "mkfs.fat -F32",
        "mount": "/boot/efi",
    },
    "root": {
        "size":  "128GiB",
        "type":  "ext4",
        "format": "mkfs.ext4",
        "mount": "/",
    },
    "swap": {
        "size":  "64GiB",
        "type":  "linuxswap",
        "format": "mkswap",
    },
    "opt": {
        "size":  "128GiB",
        "type":  "ext4",
        "format": "mkfs.ext4",
        "mount": "/opt",
    },
    "var": {
        # no size => might use the rest of the disk
        "type":  "ext4",
        "format": "mkfs.ext4",
        "mount": "/var",
    },
    "home": {
        # no size => might use the rest of the disk
        "type":  "ext4",
        "format": "mkfs.ext4",
        "mount": "/home",
    },
}

##############################################################################
# STEP 2: Utility function to run shell commands safely
##############################################################################

def run_cmd(cmd):
    """Run a shell command and return stdout; raise SystemExit on error."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        raise SystemExit(f"Command failed: {cmd}")
    return result.stdout.strip()

##############################################################################
# STEP 3: Function to list and display all block devices
##############################################################################

def list_all_block_devices():
    """
    Uses lsblk to retrieve *all* block devices (disks, partitions, loops, etc.)
    with columns: NAME, MAJ:MIN, RM, SIZE, RO, TYPE, MOUNTPOINTS.
    
    Prints them in a table for the user, then returns a list of device paths
    whose TYPE is 'disk' (e.g., /dev/sda, /dev/nvme0n1).
    """
    columns = ["NAME","MAJ:MIN","RM","SIZE","RO","TYPE","MOUNTPOINTS"]
    # -r = raw output, -n = no headings
    cmd = f"lsblk -rno {','.join(columns)}"
    output = run_cmd(cmd)

    # Prepare data for printing
    rows = []
    for line in output.splitlines():
        # Split into up to 7 columns; MOUNTPOINTS may contain spaces if multiple mountpoints
        # so we split into 6 columns max, then treat the remainder as MOUNTPOINTS
        parts = line.split(None, 6)
        if len(parts) < 6:
            continue

        name       = parts[0]
        maj_min    = parts[1]
        rm         = parts[2]
        size       = parts[3]
        ro         = parts[4]
        typ        = parts[5]
        mountpoint = parts[6] if len(parts) == 7 else ""

        rows.append([name, maj_min, rm, size, ro, typ, mountpoint])

    # Print a table header
    header = ["NAME","MAJ:MIN","RM","SIZE","RO","TYPE","MOUNTPOINTS"]
    print("\n=== All Block Devices (lsblk) ===")
    print("-"*75)
    print("{:<10} {:<7} {:<2} {:>7} {:>2} {:<6} {}".format(*header))
    print("-"*75)
    for r in rows:
        print("{:<10} {:<7} {:<2} {:>7} {:>2} {:<6} {}".format(*r))

    # Extract only those devices that are TYPE="disk"
    # For each disk, we'll build a full path: e.g. /dev/sda or /dev/nvme0n1
    disks = []
    for r in rows:
        (name, maj_min, rm, size, ro, typ, mountpoint) = r
        if typ == "disk":
            # The actual device path is "/dev/NAME", e.g. /dev/sda
            disk_path = f"/dev/{name}"
            disks.append(disk_path)

    return sorted(disks)

##############################################################################
# STEP 4: Listing partitions and printing in a nice table
##############################################################################

def list_partitions_with_parted(device):
    """
    Use parted in machine-readable mode to list partitions.
    Return a list of dicts with fields: number, start, end, size, fs, name, flags
    """
    # Use -s (script mode) to avoid any interactive prompts.
    cmd = f"parted -s -m {device} unit MiB print"
    output = run_cmd(cmd)

    partition_entries = []
    for line in output.splitlines():
        fields = line.split(":")
        if not fields:
            continue
        try:
            part_num = int(fields[0])  # partition number
        except ValueError:
            continue  # skip lines that aren't partition lines

        # parted -m format => num : start : end : size : fs : name : flags
        start    = fields[1]
        end      = fields[2]
        size     = fields[3]
        fs       = fields[4]
        pname    = fields[5] if len(fields) > 5 else ""
        flags    = fields[6] if len(fields) > 6 else ""

        partition_entries.append({
            "number": part_num,
            "start":  start,
            "end":    end,
            "size":   size,
            "fs":     fs,
            "name":   pname,
            "flags":  flags
        })
    return partition_entries

def print_partitions_table(device, partitions):
    """
    Print a table of the partitions discovered on 'device'.
    """
    headers = ["#","Start","End","Size","FS","Name","Flags"]
    rows = []
    for p in partitions:
        rows.append([
            str(p["number"]),
            p["start"],
            p["end"],
            p["size"],
            p["fs"],
            p["name"],
            p["flags"],
        ])
    print(f"\nPartitions on {device}:")
    print("-"*60)
    print("{:<3} {:>7} {:>7} {:>7} {:>8} {:>15} {:>10}".format(*headers))
    print("-"*60)
    for r in rows:
        print("{:<3} {:>7} {:>7} {:>7} {:>8} {:>15} {:>10}".format(*r))

##############################################################################
# STEP 5: Checking for desired labels and applying logic (placeholder)
##############################################################################

def apply_label_logic(device, partitions):
    """
    Compare existing partitions on 'device' to the DESIRED_PARTITIONS dictionary:
      - If the label is found, skip creation.
      - If not found, we "would create" it.
    
    This is a simplified placeholder. Extend for actual create/format calls.
    """
    existing_labels = { p["name"] for p in partitions if p["name"] }

    for desired_label, config in DESIRED_PARTITIONS.items():
        if desired_label in existing_labels:
            print(f"  - Label '{desired_label}' already exists on {device}, skipping creation.")
        else:
            print(f"  - Label '{desired_label}' not found on {device}, would create: size={config.get('size','remaining')} type={config['type']}")

##############################################################################
# MAIN
##############################################################################

def main():
    # 1) List ALL block devices in a table, get only those with TYPE=disk
    all_disks = list_all_block_devices()
    if not all_disks:
        print("\nNo disk-type devices found on the system!")
        sys.exit(0)

    print("\nDisk devices to consider for partitioning:", all_disks)

    # 2) For demonstration, we simply iterate over each discovered disk
    #    and show existing partitions + apply label logic. In a real script,
    #    you'd prompt the user which disk(s) to use, etc.
    for dev in all_disks:
        parts = list_partitions_with_parted(dev)
        print_partitions_table(dev, parts)
        apply_label_logic(dev, parts)

if __name__ == "__main__":
    main()
