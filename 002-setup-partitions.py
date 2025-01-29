#!/usr/bin/env python3

import subprocess
import sys
import re

def list_disk_devices():
    """
    Use lsblk to list devices of TYPE='disk'.
    Returns a list of (dev_path, dev_type) tuples, for example:
      [("/dev/sda", "sd"), ("/dev/nvme0n1", "nvme"), ...]
    """
    # lsblk -ln -o NAME,TYPE => prints lines like:
    #   sda  disk
    #   sda1 part
    #   nvme0n1 disk
    #   nvme0n1p1 part
    cmd = "lsblk -ln -o NAME,TYPE"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)

    devices = []
    for line in result.stdout.strip().splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        name, typ = parts[0], parts[1]
        if typ == "disk":
            # Construct full path
            dev_path = f"/dev/{name}"

            # Determine device_type: "sd" or "nvme" or fallback "other"
            if re.match(r"^sd[a-z]+$", name):
                dev_type = "sd"
            elif re.match(r"^nvme\d+n\d+$", name):
                dev_type = "nvme"
            else:
                dev_type = "other"

            devices.append((dev_path, dev_type))
    return devices

def prompt_device_usage(dev_path, dev_type):
    """
    Prompt user if this device should be used. If yes, ask how it will be used:
    - system
    - home
    - none
    - or custom label
    Returns a dict with:
      {
        "use_device": bool,
        "device_use": str,    # e.g. 'system', 'home', 'none', 'store', etc.
        "device":     str,    # e.g. '/dev/sda'
        "device_type": str,   # e.g. 'sd', 'nvme'
      }
    """
    print(f"\nFound device: {dev_path} ({dev_type})")

    # Ask if user wants to use this device
    use_resp = input("  Use this device for partitioning? (y/n) ").strip().lower()
    if use_resp not in ["y", "yes"]:
        return {
            "use_device": False,
            "device_use": None,
            "device": dev_path,
            "device_type": dev_type,
        }

    # They want to use it => ask usage
    print("  How do you want to use it?")
    print("   1) system")
    print("   2) home")
    print("   3) none   (create partitions but do not mount, or skip usage?)")
    print("   4) custom (e.g. store, opt, var, etc.)")
    choice = input("  Enter choice [1-4]: ").strip()

    if choice == "1":
        device_use = "system"
    elif choice == "2":
        device_use = "home"
    elif choice == "3":
        device_use = "none"
    elif choice == "4":
        device_use = input("Enter custom label (e.g., store, var, opt): ").strip()
        if not device_use:
            device_use = "custom"
    else:
        print("  Invalid choice, defaulting to 'none'")
        device_use = "none"

    return {
        "use_device": True,
        "device_use": device_use,
        "device": dev_path,
        "device_type": dev_type,
    }

def main():
    print("Discovering disk devices (including /dev/sdX and /dev/nvmeXnY)...")
    all_disks = list_disk_devices()

    if not all_disks:
        print("No disk devices found.")
        sys.exit(0)

    devices_dict = []
    for dev_path, dev_type in all_disks:
        usage_info = prompt_device_usage(dev_path, dev_type)
        devices_dict.append(usage_info)

    print("\n=== Summary of Selections ===")
    for d in devices_dict:
        print(d)

    # If you'd like to do something more advanced (e.g. write to JSON, or proceed to partitioning), do so here.
    # For example:
    # import json
    # print(json.dumps(devices_dict, indent=2))

if __name__ == "__main__":
    main()
