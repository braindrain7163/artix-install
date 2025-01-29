#!/usr/bin/env python3

import json
import re
import subprocess

def run_cmd(cmd):
    """
    Run a shell command, return stdout on success, raise an exception on error.
    """
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    result.check_returncode()
    return result.stdout.strip()

def get_parted_json():
    """
    Runs 'parted -j -l' to get JSON output for all disks.
    parted may return multiple JSON objects, one per disk.
    We'll split them and parse into a list of Python objects.
    
    Returns something like:
      [
         { "disk": {...} },
         { "disk": {...} },
         ...
      ]
    """
    cmd = "sudo parted -j -l"
    output = run_cmd(cmd)
    # parted often returns multiple top-level JSON objects separated by newlines.
    # We'll split on boundaries where a line ends with } and the next line starts with {.
    parted_entries = []
    # Safely split multiple JSON objects if they exist:
    chunks = re.split(r'(?<=\})\s*\n(?=\{)', output)
    for chunk in chunks:
        chunk = chunk.strip()
        if chunk:
            parted_entries.append(json.loads(chunk))
    return parted_entries

def get_lsblk_json():
    """
    Runs 'lsblk -f -J' to get a JSON listing of all block devices with
    filesystem info: FSTYPE, LABEL, UUID, FSAVAIL, FSUSE%, MOUNTPOINTS, etc.
    
    Returns a dict with top-level key "blockdevices", e.g.:
    {
      "blockdevices": [
        {
          "name": "nvme0n1",
          "type": "disk",
          "children": [
            {
              "name": "nvme0n1p1",
              "fstype": "vfat",
              "label": "efi",
              "uuid": "77A7-7C85",
              ...
            },
            ...
          ]
        },
        ...
      ]
    }
    """
    cmd = "lsblk -f -J"
    output = run_cmd(cmd)
    return json.loads(output)

def build_partition_devpath(disk_path, part_number):
    """
    Given a disk path (e.g. /dev/nvme0n1 or /dev/sda) and a partition number (int),
    return the appropriate partition device name:
      - /dev/nvme0n1 + 'p' + number => /dev/nvme0n1p2 (for NVMe)
      - /dev/sda + number => /dev/sda2 (for typical sdX)
    
    This is a common convention for Linux:
      If the base name contains 'nvme', we insert 'p' before the partition number.
      Otherwise, we just append the number.
    """
    if "nvme" in disk_path:
        # e.g. /dev/nvme0n1 -> /dev/nvme0n1p1
        return f"{disk_path}p{part_number}"
    else:
        # e.g. /dev/sda -> /dev/sda1
        return f"{disk_path}{part_number}"

def find_lsblk_entry_by_name(lsblk_blockdevices, dev_name):
    """
    Recursively search the lsblk JSON "blockdevices" tree to find
    the entry whose "name" equals dev_name (e.g. 'nvme0n1p2').

    Returns the matching dict or None if not found.
    """
    for device in lsblk_blockdevices:
        if device["name"] == dev_name:
            return device
        # Recurse into children if present
        if "children" in device and device["children"]:
            found = find_lsblk_entry_by_name(device["children"], dev_name)
            if found:
                return found
    return None

def merge_parted_and_lsblk():
    """
    Main function to:
    1) Get parted JSON data (possibly multiple disks).
    2) Get lsblk JSON data.
    3) For each parted disk's partition, figure out the device name
       (e.g. "nvme0n1p2"), find it in lsblk, and attach those fields.
    4) Return the final combined data as a list of parted disk objects,
       each with extra fields in partitions.
    """
    parted_data = get_parted_json()  # list of parted objects
    lsblk_data = get_lsblk_json()    # dict with "blockdevices"

    if "blockdevices" not in lsblk_data:
        # Malformed or no blockdevices
        return parted_data  # no merging possible

    for parted_obj in parted_data:
        # parted_obj typically has the shape: { "disk": {...} }
        disk_info = parted_obj.get("disk", {})
        disk_path = disk_info.get("path", "")    # e.g. "/dev/nvme0n1"
        partitions = disk_info.get("partitions", [])

        for part in partitions:
            # parted partition object has "number": 1, 2, 3, ...
            number = part["number"]
            # build the partition device path, e.g. "/dev/nvme0n1p2"
            part_dev = build_partition_devpath(disk_path, number)

            # lsblk 'name' is just the basename, e.g. "nvme0n1p2"
            # so we have to strip off "/dev/" from part_dev
            dev_basename = part_dev.replace("/dev/", "")

            # find the matching entry in lsblk
            lsblk_entry = find_lsblk_entry_by_name(lsblk_data["blockdevices"], dev_basename)
            if lsblk_entry:
                # Attach whichever fields we care about to parted's partition object.
                # For example: "fstype", "label", "uuid", "mountpoints", ...
                part["lsblk-fstype"]       = lsblk_entry.get("fstype", "")
                part["lsblk-fsver"]        = lsblk_entry.get("fsver", "")
                part["lsblk-label"]        = lsblk_entry.get("label", "")
                part["lsblk-uuid"]         = lsblk_entry.get("uuid", "")
                part["lsblk-fsavail"]      = lsblk_entry.get("fsavail", "")
                part["lsblk-fsuse%"]       = lsblk_entry.get("fsuse%", "")
                part["lsblk-mountpoints"]  = lsblk_entry.get("mountpoints", [])

    return parted_data

def main():
    combined_data = merge_parted_and_lsblk()

    # Print or return as JSON
    print(json.dumps(combined_data, indent=2))

if __name__ == "__main__":
    main()
