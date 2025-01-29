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
        "device_use": "system"
    },
    "root": {
        "size":  "128GiB",
        "type":  "ext4",
        "format": "mkfs.ext4",
        "mount": "/",
        "device_use": "system"
    },
    "swap": {
        "size":  "64GiB",
        "type":  "linuxswap",
        "format": "mkswap",
        "device_use": "system"
    },
    "opt": {
        "size":  "128GiB",
        "type":  "ext4",
        "format": "mkfs.ext4",
        "mount": "/opt",
        "device_use": "system"
    },
    "var": {
        # no size => might use the rest of the disk
        "type":  "ext4",
        "format": "mkfs.ext4",
        "mount": "/var",
        "device_use": "system"
    },
    "home": {
        # no size => might use the rest of the disk
        "type":  "ext4",
        "format": "mkfs.ext4",
        "mount": "/home",
        "device_use": "home"
    },
}
#!/usr/bin/env python3

import json
import re
import subprocess
import sys

##############################################################################
# 1) Desired partitions (example placeholder)
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
        # no size => might use rest of the disk
        "type":  "ext4",
        "format": "mkfs.ext4",
        "mount": "/var",
    },
    "home": {
        # no size => might use rest of the disk
        "type":  "ext4",
        "format": "mkfs.ext4",
        "mount": "/home",
    },
}

##############################################################################
# 2) Basic shell command helper
##############################################################################

def run_cmd(cmd):
    """
    Run a shell command and return stdout if successful.
    Raises SystemExit on error.
    """
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        raise SystemExit(f"Command failed: {cmd}")
    return result.stdout.strip()

##############################################################################
# 3) Merge parted -j -l + lsblk -f -J
##############################################################################

def get_parted_json():
    """
    Runs 'sudo parted -j -l' (JSON output for parted).
    parted may return multiple JSON objects, each containing e.g.:
      {
        "disk": {
            "path": "/dev/sda",
            "size": "256GB",
            "model": "...",
            "transport": "ata",
            ...
            "partitions": [...]
        }
      }
    We'll parse them into a list: [ {...}, {...}, ... ]
    """
    cmd = "sudo parted -j -l"
    output = run_cmd(cmd)
    # parted often returns multiple JSON objects in sequence (no top-level array).
    # We split them carefully using a regex that detects the boundary between objects.
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
    Runs 'lsblk -f -J' to get a JSON listing of block devices + filesystem info.
    Returns a dict:
      {
        "blockdevices": [
          {
            "name": "sda",
            "type": "disk",
            "children": [
              { "name": "sda1", "fstype": "ext4", "label": "root", ...},
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

def build_partition_devpath(disk_path, part_num):
    """
    e.g. /dev/nvme0n1 + 2 => /dev/nvme0n1p2
         /dev/sda + 1 => /dev/sda1
    """
    if "nvme" in disk_path:
        return f"{disk_path}p{part_num}"
    else:
        return f"{disk_path}{part_num}"

def find_lsblk_entry_by_name(lsblk_blockdevices, dev_name):
    """
    Recursively search lsblk's blockdevices for "name" == dev_name.
    Returns that entry's dict or None.
    """
    for device in lsblk_blockdevices:
        if device["name"] == dev_name:
            return device
        if "children" in device and device["children"]:
            found = find_lsblk_entry_by_name(device["children"], dev_name)
            if found:
                return found
    return None

def merge_parted_and_lsblk():
    """
    1) parted_data = get_parted_json() => list of parted disk objects
    2) lsblk_data = get_lsblk_json() => dict with "blockdevices"
    3) For each parted disk's partition, find matching lsblk entry and attach fields.
    Returns parted_data with extra "lsblk-*" fields in partitions.
    """
    parted_data = get_parted_json()
    lsblk_data  = get_lsblk_json()

    if "blockdevices" not in lsblk_data:
        return parted_data

    for parted_obj in parted_data:
        disk_info  = parted_obj.get("disk", {})
        disk_path  = disk_info.get("path", "")
        partitions = disk_info.get("partitions", [])

        for part in partitions:
            number  = part["number"]
            partdev = build_partition_devpath(disk_path, number)
            dev_basename = partdev.replace("/dev/", "")  # e.g. 'sda1'
            match = find_lsblk_entry_by_name(lsblk_data["blockdevices"], dev_basename)
            if match:
                # Attach info from lsblk
                part["lsblk-fstype"]      = match.get("fstype", "")
                part["lsblk-label"]       = match.get("label", "")
                part["lsblk-uuid"]        = match.get("uuid", "")
                part["lsblk-mountpoints"] = match.get("mountpoints", [])
                part["lsblk-fsavail"]     = match.get("fsavail", "")
                part["lsblk-fsuse%"]      = match.get("fsuse%", "")

    return parted_data

##############################################################################
# 4) Get a list of drives (disk_path, device_type) from merged data
##############################################################################

def infer_device_type(disk_path, parted_disk):
    """
    Attempt to determine device_type based on parted's "transport" or the disk path.
    parted might store 'transport': 'nvme', 'ata', etc.
    If the path looks like /dev/sdX => 'sd'
       if /dev/nvme... => 'nvme'
       otherwise => parted_disk["transport"] or 'other'
    """
    transport = parted_disk.get("transport", "").lower()  # e.g. "nvme", "ata"
    if re.match(r"^/dev/sd[a-z]+$", disk_path):
        return "sd"
    if "nvme" in disk_path:
        return "nvme"
    if transport:
        return transport  # e.g. "ata", "scsi"
    return "other"

def get_drives_from_merged(merged_data):
    """
    merged_data is a list of parted JSON objects, each typically shaped like:
      {
        "disk": {
          "path": "/dev/sda",
          "size": "256GB",
          "transport": "ata",
          "partitions": [...]
        }
      }
    We'll gather each "disk.path" and infer device_type.

    Returns a list of (disk_path, device_type) for each parted disk object.
    """
    drives = []
    for parted_obj in merged_data:
        disk_info = parted_obj.get("disk", {})
        path = disk_info.get("path", "")
        if not path:
            continue
        # parted_l might also show CD-ROM or loop devices, but typically parted
        # only shows real block devices with partition tables. We'll assume they're valid.
        dev_type = infer_device_type(path, disk_info)
        drives.append((path, dev_type))
    return drives

##############################################################################
# 5) Prompt user for usage => devices_dict
##############################################################################

def prompt_for_drive_usage(drives):
    """
    For each (disk_path, device_type), ask the user:
      - Use this device for partitioning? (y/n)
      - If yes, system, home, none, or custom?
    Returns a list of dicts:

    [
      {
        "use_device": True,
        "device_use": "system",
        "device": "/dev/nvme0n1",
        "device_type": "nvme",
      },
      ...
    ]
    """
    devices_dict = []
    for (dev_path, dev_type) in drives:
        print(f"\nDiscovered drive: {dev_path} ({dev_type})")
        ans = input("  Use this device for partitioning? (y/n): ").strip().lower()
        if ans not in ["y", "yes"]:
            devices_dict.append({
                "use_device": False,
                "device_use": None,
                "device": dev_path,
                "device_type": dev_type
            })
            continue

        # If user says "yes", ask how
        print("  How do you want to use this drive?")
        print("   1) system")
        print("   2) home")
        print("   3) none   (create partitions but no auto-mount usage)")
        print("   4) custom (e.g. store, var, opt, etc.)")
        choice = input("  Enter choice [1-4]: ").strip()

        if choice == "1":
            device_use = "system"
        elif choice == "2":
            device_use = "home"
        elif choice == "3":
            device_use = "none"
        elif choice == "4":
            custom_label = input("    Enter custom label (e.g. store, var, opt): ").strip()
            device_use = custom_label if custom_label else "custom"
        else:
            print("  Invalid choice, defaulting to 'none'")
            device_use = "none"

        devices_dict.append({
            "use_device": True,
            "device_use": device_use,
            "device": dev_path,
            "device_type": dev_type
        })

    return devices_dict

##############################################################################
# 6) Example "apply_label_logic" placeholder
##############################################################################

def apply_label_logic(devices_dict, merged_data):
    """
    A placeholder function that shows how you might integrate
    the desired partitions and the final device usage.

    'devices_dict' is a list of:
        {
            "use_device": True/False,
            "device_use": "system"/"home"/"none"/<custom>,
            "device": "/dev/nvme0n1",
            "device_type": "nvme"
        }

    'merged_data' is parted+lsblk merged JSON, e.g.:
        [
          {
            "disk": {
              "path": "/dev/nvme0n1",
              "partitions": [
                {
                  "number": 1,
                  "filesystem": "fat32",
                  "lsblk-label": "EFI",
                  ...
                },
                ...
              ]
            }
          },
          ...
        ]
    You can decide how to create or skip partitions based on "device_use".
    """
    # Build a map of disk_path -> parted_object for easy lookup
    parted_map = {}
    for obj in merged_data:
        disk_path = obj.get("disk", {}).get("path", "")
        parted_map[disk_path] = obj

    # For each device the user wants to use, do something
    for dev_info in devices_dict:
        if not dev_info["use_device"]:
            print(f"\nSkipping {dev_info['device']} (user chose not to use).")
            continue

        disk_path  = dev_info["device"]
        usage_type = dev_info["device_use"]
        parted_obj = parted_map.get(disk_path)
        if not parted_obj:
            print(f"\nNo parted data found for {disk_path}. Strange, skipping.")
            continue

        print(f"\nDevice {disk_path} chosen for '{usage_type}'.")
        # parted_obj["disk"]["partitions"] => existing partitions
        # You could check if "EFI" is missing, then create it, etc.
        # For demonstration, just print the existing parted+lsblk data:
        for p in parted_obj["disk"].get("partitions", []):
            label = p.get("lsblk-label", "")
            fs = p.get("lsblk-fstype", "") or p.get("filesystem", "")
            print(f"  Found partition: number={p['number']} label={label} fs={fs}")

        # If usage_type == "system", you might ensure EFI + root partition exist, etc.
        # If usage_type == "home", ensure 'home' partition is present. And so on.
        # This is where you'd do parted mkpart or mkfs.* calls in real usage.

##############################################################################
# MAIN
##############################################################################

def main():
    # 1) Merge parted -j -l + lsblk -f -J data
    merged_data = merge_parted_and_lsblk()
    if not merged_data:
        print("No data from parted or no disks found. Exiting.")
        sys.exit(1)

    # 2) Extract a list of drives (disk_path, device_type) from merged data
    drives = get_drives_from_merged(merged_data)
    if not drives:
        print("No drives discovered in parted JSON data. Exiting.")
        sys.exit(1)

    # 3) Prompt user how to use each drive
    devices_dict = prompt_for_drive_usage(drives)

    # 4) Example: apply label logic or partition logic
    apply_label_logic(devices_dict, merged_data)

    # 5) Optionally print final devices_dict
    print("\n=== Final devices_dict ===")
    for dev in devices_dict:
        print(dev)

if __name__ == "__main__":
    main()
