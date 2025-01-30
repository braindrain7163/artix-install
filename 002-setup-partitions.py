#!/usr/bin/env python3

import json
import re
import subprocess
import sys

##############################################################################
# 1) Desired Partitions
##############################################################################

DESIRED_PARTITIONS = {
    "efi": {
        "size":  "512MiB",
        "type":  "fat32",
        "format": False,
        "file_system_type": "mkfs.fat -F32",
        "mount": "/boot/efi",
        "partition_location": "system"
    },
    "root": {
        "size":  "128GiB",
        "type":  "ext4",
        "format": True,
        "file_system_type": "mkfs.ext4",
        "mount": "/",
        "partition_location": "system"
    },
    "swap": {
        "size":  "64GiB",
        "type":  "linuxswap",
        "file_system_type": "mkswap",
        "partition_location": "system"
    },
    "opt": {
        "size":  "128GiB",
        "type":  "ext4",
        "format": False,
        "file_system_type": "mkfs.ext4",
        "mount": "/opt",
        "partition_location": "system"
    },
    "var": {
        # no size => might use the rest of the disk
        "type":  "ext4",
        "format": False,
        "file_system_type": "mkfs.ext4",
        "mount": "/var",
        "partition_location": "system"
    },
    "home": {
        # no size => might use the rest of the disk
        "type":  "ext4",
        "format": False,
        "file_system_type": "mkfs.ext4",
        "mount": "/home",
        "partition_location": "home"
    },
}

##############################################################################
# 2) Utility: run_cmd
##############################################################################

def run_cmd(cmd):
    """
    Run a shell command and return stdout if successful.
    Raises SystemExit on error with the stderr message.
    """
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        raise SystemExit(f"Command failed: {cmd}")
    return result.stdout.strip()

##############################################################################
# 3) List all block devices (TYPE='disk') with lsblk
##############################################################################

def list_all_block_devices():
    """
    Uses lsblk to retrieve *all* block devices (disks, partitions, loops, etc.)
    with columns: NAME, MAJ:MIN, RM, SIZE, RO, TYPE, MOUNTPOINTS.

    Prints them in a table for the user, then returns a list of device paths
    whose TYPE is 'disk' (e.g., /dev/sda, /dev/nvme0n1).
    """
    columns = ["NAME","MAJ:MIN","RM","SIZE","RO","TYPE","MOUNTPOINTS"]
    cmd = f"lsblk -rno {','.join(columns)}"
    output = run_cmd(cmd)

    rows = []
    for line in output.splitlines():
        # Because MOUNTPOINTS might contain spaces if multiple mountpoints,
        # split into at most 6 columns + 1 remainder for MOUNTPOINTS
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
    disks = []
    for row in rows:
        (name, maj_min, rm, size, ro, typ, mountpoint) = row
        if typ == "disk":
            disk_path = f"/dev/{name}"
            disks.append(disk_path)

    return sorted(disks)

##############################################################################
# 4) Merge parted -j -l + lsblk -f -J
##############################################################################

def get_parted_json():
    """
    Runs 'sudo parted -j -l' to get JSON output for all disks.
    parted may return multiple JSON objects (one per disk).
    """
    cmd = "sudo parted -j -l"
    output = run_cmd(cmd)
    import re
    chunks = re.split(r'(?<=\})\s*\n(?=\{)', output.strip())
    parted_entries = []
    for chunk in chunks:
        chunk = chunk.strip()
        if chunk:
            parted_entries.append(json.loads(chunk))
    return parted_entries

def get_lsblk_json():
    """
    Runs 'lsblk -f -J' => returns a dict with "blockdevices": [...]
    """
    cmd = "lsblk -f -J"
    output = run_cmd(cmd)
    return json.loads(output)

def build_partition_devpath(disk_path, part_num):
    """
    /dev/nvme0n1 + 1 => /dev/nvme0n1p1
    /dev/sda + 1 => /dev/sda1
    """
    if "nvme" in disk_path:
        return f"{disk_path}p{part_num}"
    else:
        return f"{disk_path}{part_num}"

def find_lsblk_entry_by_name(blockdevices, dev_name):
    """
    Recursively search blockdevices for an entry with "name" = dev_name.
    Return that entry or None.
    """
    for device in blockdevices:
        if device.get("name") == dev_name:
            return device
        if "children" in device and device["children"]:
            found = find_lsblk_entry_by_name(device["children"], dev_name)
            if found:
                return found
    return None

def merge_parted_and_lsblk():
    """
    1) parted_data = get_parted_json()
    2) lsblk_data = get_lsblk_json()
    3) For each parted disk's partition, find matching lsblk entry => attach fields.
    Returns parted_data with extra "lsblk-*" fields in partitions.
    """
    parted_data = get_parted_json()
    lsblk_data  = get_lsblk_json()

    blockdevices = lsblk_data.get("blockdevices", [])
    if not blockdevices:
        return parted_data

    for pdisk in parted_data:
        disk_info = pdisk.get("disk", {})
        disk_path = disk_info.get("path", "")
        parts     = disk_info.get("partitions", [])

        for part in parts:
            pnum = part["number"]
            part_dev = build_partition_devpath(disk_path, pnum)
            dev_basename = part_dev.replace("/dev/", "")
            match = find_lsblk_entry_by_name(blockdevices, dev_basename)
            if match:
                part["lsblk-fstype"]      = match.get("fstype", "")
                part["lsblk-label"]       = match.get("label", "")
                part["lsblk-uuid"]        = match.get("uuid", "")
                part["lsblk-mountpoints"] = match.get("mountpoints", [])
                part["lsblk-fsavail"]     = match.get("fsavail", "")
                part["lsblk-fsuse%"]      = match.get("fsuse%", "")
    return parted_data

##############################################################################
# 5) Prompt user for usage => devices_dict
##############################################################################

def guess_device_type(disk_path):
    """
    Simple guess for device_type: 'sd', 'nvme', or 'other'.
    """
    if re.match(r"^/dev/sd[a-z]+$", disk_path):
        return "sd"
    if "nvme" in disk_path:
        return "nvme"
    return "other"

def prompt_device_usage(all_disks):
    """
    For each disk in all_disks, ask user if they want to use it. If yes, ask usage:
    'system', 'home', 'none', or custom label.

    Returns a list of dicts:
    [
      {
        "use_device": True/False,
        "partition_location": "system"/"home"/"none"/...,
        "device": "/dev/sda",
        "device_type": "sd"
      },
      ...
    ]
    """
    devices_dict = []

    for disk in all_disks:
        dev_type = guess_device_type(disk)
        print(f"\nFound device: {disk} (type={dev_type})")
        ans = input("  Use this device for partitioning? (y/n): ").strip().lower()
        if ans not in ["y", "yes"]:
            devices_dict.append({
                "use_device": False,
                "partition_location": None,
                "device": disk,
                "device_type": dev_type
            })
            continue

        # If user says "yes", ask usage
        print("  How do you want to use this drive?")
        print("   1) system")
        print("   2) home")
        print("   3) none  (create partitions but no auto mount usage?)")
        print("   4) custom (store, var, opt, etc.)")
        choice = input("  Enter choice [1-4]: ").strip()

        if choice == "1":
            partition_location = "system"
        elif choice == "2":
            partition_location = "home"
        elif choice == "3":
            partition_location = "none"
        elif choice == "4":
            custom_label = input("    Enter custom label (e.g. store, var, opt): ").strip()
            partition_location = custom_label if custom_label else "custom"
        else:
            print("  Invalid choice, defaulting to 'none'")
            partition_location = "none"

        devices_dict.append({
            "use_device": True,
            "partition_location": partition_location,
            "device": disk,
            "device_type": dev_type
        })

    return devices_dict

##############################################################################
# 6) Assign Partitions Based on partition_location
##############################################################################

def assign_partitions(devices_dict, merged_data):
    """
    For each disk the user wants to use, find all DESIRED_PARTITIONS entries
    that match the same 'partition_location'. If a partition label in DESIRED_PARTITIONS
    doesn't exist on the disk, we "would create" it (placeholder). If it exists,
    we skip.

    merged_data is a list of parted disk objects, e.g.:
    [
      {
        "disk": {
          "path": "/dev/sda",
          "partitions": [
            {
              "number": 1,
              "lsblk-fstype": "vfat",
              "lsblk-label": "EFI",
              ...
            },
            ...
          ]
        }
      },
      ...
    ]
    """
    # Build a map from disk_path -> parted disk object
    parted_map = {}
    for dobj in merged_data:
        disk_path = dobj.get("disk", {}).get("path", "")
        parted_map[disk_path] = dobj

    # For each device the user wants to use, find partitions to create
    for dev_info in devices_dict:
        if not dev_info["use_device"]:
            print(f"\nSkipping {dev_info['device']} (user chose not to use).")
            continue

        disk_path = dev_info["device"]
        usage = dev_info["partition_location"]

        parted_obj = parted_map.get(disk_path)
        if not parted_obj:
            print(f"\nNo parted info for {disk_path}. Possibly parted didn't see it. Skipping.")
            continue

        print(f"\nAssigning partitions for device: {disk_path} (usage={usage})")

        # Get existing filesystem labels from the merged parted+lsblk data
        existing_labels = set()
        for p in parted_obj["disk"].get("partitions", []):
            fslabel = p.get("lsblk-label", "")
            if fslabel:
                existing_labels.add(fslabel.lower())

        # For each partition in DESIRED_PARTITIONS, check if it matches usage
        for part_label, config in DESIRED_PARTITIONS.items():
            # e.g. "efi", "root", "home" => config["partition_location"] in ["system","home"]
            desired_use = config.get("partition_location", "none")
            if desired_use.lower() != usage.lower():
                # Not for this device usage
                continue

            # Check if a partition with that label already exists (case-insensitive match)
            if part_label.lower() in existing_labels:
                print(f"  - Partition '{part_label}' already present on {disk_path}. Skipping.")
            else:
                # We WOULD create + format it here. Placeholder:
                print(f"  - Partition '{part_label}' does NOT exist on {disk_path}.")
                print(f"    Would create: size={config.get('size','remaining')} type={config['type']}")
                print(f"    Then format with: {config['file_system_type']}")
                if "mount" in config:
                    print(f"    Then mount at: {config['mount']}")
                # Example real parted commands might be:
                # parted -s {disk_path} mkpart primary ext4 startMiB endMiB
                # run_cmd("mkfs.ext4 /dev/sdaX")
                # We'll leave that unimplemented for now.

##############################################################################
# MAIN
##############################################################################

def main():
    # 1) Show all block devices & pick which to use
    all_disks = list_all_block_devices()
    if not all_disks:
        print("\nNo disk-type devices found on system!")
        sys.exit(1)

    devices_dict = prompt_device_usage(all_disks)

    # 2) Merge parted + lsblk once
    merged_data = merge_parted_and_lsblk()
    if not merged_data:
        print("No parted or lsblk data found. Exiting.")
        sys.exit(1)

    # 3) Assign partitions based on usage
    assign_partitions(devices_dict, merged_data)

    # 4) Show final choices
    print("\n=== Final devices_dict ===")
    for d in devices_dict:
        print(d)

if __name__ == "__main__":
    main()
