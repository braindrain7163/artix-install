#!/usr/bin/env python3

import json
import os
import re
import subprocess
import sys

##############################################################################
# STEP 1: Desired partition labels (placeholder example)
##############################################################################

DESIRED_PARTITIONS = {
    "efi": {
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
    """
    Run a shell command and return stdout on success.
    Raises SystemExit on error with the stderr message.
    """
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        raise SystemExit(f"Command failed: {cmd}")
    return result.stdout.strip()

##############################################################################
# STEP 3: Function to list and display all block devices (TYPE='disk')
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
# STEP 4: Merging parted -j -l with lsblk -f -J
##############################################################################

def get_parted_json():
    """
    Runs 'sudo parted -j -l' to get JSON output for all disks.
    parted may return multiple JSON objects (one per disk) separated by newlines.
    We'll split them properly and parse into a list of Python objects.
    """
    cmd = "sudo parted -j -l"
    output = run_cmd(cmd)
    # parted typically returns consecutive JSON objects, each for a disk,
    # often separated by newlines. We'll split carefully:
    import re
    chunks = re.split(r'(?<=\})\s*\n(?=\{)', output.strip())
    parted_entries = []
    for chunk in chunks:
        chunk = chunk.strip()
        if chunk:
            parted_entries.append(json.loads(chunk))
    return parted_entries  # e.g. [ { "disk": {...}}, { "disk": {...}} ]

def get_lsblk_json():
    """
    Runs 'lsblk -f -J' to get a JSON listing of all block devices with
    filesystem info: FSTYPE, LABEL, UUID, FSAVAIL, FSUSE%, MOUNTPOINTS, etc.

    Returns a dict with top-level key "blockdevices".
    """
    cmd = "lsblk -f -J"
    output = run_cmd(cmd)
    return json.loads(output)

def build_partition_devpath(disk_path, part_number):
    """
    Given a disk path (e.g. /dev/nvme0n1 or /dev/sda) and a partition number,
    return the appropriate partition device name:
      - /dev/nvme0n1p<part_number> if 'nvme' is in the disk_path
      - /dev/sda<part_number> otherwise
    """
    if "nvme" in disk_path:
        return f"{disk_path}p{part_number}"
    else:
        return f"{disk_path}{part_number}"

def find_lsblk_entry_by_name(lsblk_blockdevices, dev_name):
    """
    Recursively search the lsblk "blockdevices" structure to find
    the entry whose "name" matches dev_name (e.g. 'nvme0n1p2').

    Returns that entry (dict) or None if not found.
    """
    for device in lsblk_blockdevices:
        if device.get("name") == dev_name:
            return device
        # Recurse if children exist
        if "children" in device and device["children"]:
            found = find_lsblk_entry_by_name(device["children"], dev_name)
            if found:
                return found
    return None

def merge_parted_and_lsblk():
    """
    1) Get parted JSON data (possibly multiple disks).
    2) Get lsblk JSON data (one structure with "blockdevices").
    3) For each parted disk's partition, build the partition path
       (e.g. /dev/nvme0n1p2), find it in lsblk, and attach fields like
       fstype, label, mountpoints, etc.
    4) Return a list of parted objects with extra "lsblk-" fields
       for each partition.
    """
    parted_data = get_parted_json()   # list of { "disk": { ... } }
    lsblk_data  = get_lsblk_json()    # { "blockdevices": [ ... ] }

    if "blockdevices" not in lsblk_data:
        # No merges possible if malformed
        return parted_data

    for parted_obj in parted_data:
        disk_info   = parted_obj.get("disk", {})
        disk_path   = disk_info.get("path", "")   # e.g. /dev/nvme0n1
        partitions  = disk_info.get("partitions", [])

        for part in partitions:
            pnum = part["number"]
            part_dev = build_partition_devpath(disk_path, pnum)
            dev_basename = part_dev.replace("/dev/", "")  # e.g. nvme0n1p2

            # Look for the matching entry in lsblk
            lsblk_entry = find_lsblk_entry_by_name(lsblk_data["blockdevices"], dev_basename)
            if lsblk_entry:
                # Merge whatever fields you want from lsblk into parted data
                part["lsblk-fstype"]      = lsblk_entry.get("fstype", "")
                part["lsblk-label"]       = lsblk_entry.get("label", "")
                part["lsblk-uuid"]        = lsblk_entry.get("uuid", "")
                part["lsblk-mountpoints"] = lsblk_entry.get("mountpoints", [])
                part["lsblk-fsavail"]     = lsblk_entry.get("fsavail", "")
                part["lsblk-fsuse%"]      = lsblk_entry.get("fsuse%", "")

    return parted_data

##############################################################################
# STEP 5: Checking for desired labels and applying logic (example placeholder)
##############################################################################

def apply_label_logic(disk_obj):
    """
    Given a parted+lsblk merged disk object (from parted_data),
    compare its partitions vs. DESIRED_PARTITIONS. If a label is found,
    skip creation; if not, you might create it, etc.

    parted_data structure is something like:
    {
      "disk": {
        "path": "/dev/nvme0n1",
        "partitions": [
           {
             "number": 1,
             "start": "1049kB",
             "end": "538MB",
             "filesystem": "fat32",
             ...,
             "lsblk-fstype": "vfat",
             "lsblk-label": "efi",
             ...
           },
           ...
        ]
      }
    }
    """
    disk_path  = disk_obj["disk"].get("path", "")
    partitions = disk_obj["disk"].get("partitions", [])

    # parted -j doesn't always store a "name". Usually you see "filesystem", "flags", etc.
    # If you want to detect a GPT-partition 'label' (the parted "name"), you must set it manually.
    # Alternatively, you might check "lsblk-label" for the filesystem label.
    # For simplicity, let's treat "lsblk-label" as the 'existing label'.
    existing_fslabels = set()
    for p in partitions:
        fslabel = p.get("lsblk-label", "")
        if fslabel:
            existing_fslabels.add(fslabel)

    print(f"\nChecking desired partitions for {disk_path}")
    for desired_label, config in DESIRED_PARTITIONS.items():
        # We'll treat desired_label (e.g. "EFI", "root") as if it might match an lsblk-label.
        # If we find that label in existing_fslabels, skip creation.
        # Otherwise, we'd "create" it. This is purely example logic!
        if desired_label in existing_fslabels:
            print(f"  - Label '{desired_label}' already on {disk_path}. Skipping.")
        else:
            print(f"  - Label '{desired_label}' NOT on {disk_path}. Would create: size={config.get('size', 'remaining')} type={config['type']}")

##############################################################################
# MAIN
##############################################################################

def main():
    # 1) Show all block devices & collect only those with TYPE=disk
    all_disks = list_all_block_devices()
    if not all_disks:
        print("\nNo disk-type devices found on the system!")
        sys.exit(0)

    print("\nDisk devices to consider for partitioning:", all_disks)

    # 2) Get parted JSON + lsblk JSON, merge them
    merged_data = merge_parted_and_lsblk()
    # merged_data is a list of parted objects:
    #   [ { "disk": { path: "/dev/sda", partitions: [...]}}, { "disk": {...}}, ... ]

    # 3) For each disk object from parted, see if it is in our "all_disks" list
    #    If so, apply label logic
    for disk_obj in merged_data:
        disk_path = disk_obj["disk"].get("path", "")
        if disk_path in all_disks:
            # We'll demonstrate a basic "apply_label_logic"
            apply_label_logic(disk_obj)
        else:
            print(f"\nSkipping parted info for {disk_path} since user didn't select it.")

    # 4) If you'd like, print the final merged JSON to see parted + lsblk fields
    #    (Uncomment if desired)
    # import pprint
    # pprint.pprint(merged_data)


if __name__ == "__main__":
    main()
