#!/usr/bin/env python3

import json
import re
import subprocess
import sys
import os

##############################################################################
# DESIRED_PARTITIONS dictionary (example)
##############################################################################

DESIRED_PARTITIONS = {
    "efi": {
        "size":       "512MiB",
        "type":       "fat32",
        "format":     "true",
        "file_system":"mkfs.fat -F32",
        "mount":      "/boot/efi",
        "device_use": "system"
    },
    "root": {
        "size":       "128GiB",
        "type":       "ext4",
        "format":     "true",
        "file_system":"mkfs.ext4",
        "mount":      "/",
        "device_use": "system"
    },
    "swap": {
        "size":       "64GiB",
        "type":       "linuxswap",
        "file_system":"mkswap",
        "device_use": "system"
    },
    "opt": {
        "size":       "128GiB",
        "type":       "ext4",
        "format":     "true",
        "file_system":"mkfs.ext4",
        "mount":      "/opt",
        "device_use": "system"
    },
    "var": {
        # no size => might use the rest of the disk
        "type":       "ext4",
        "format":     "true",
        "file_system":"mkfs.ext4",
        "mount":      "/var",
        "device_use": "system"
    },
    "home": {
        # no size => might use the rest of the disk
        "type":       "ext4",
        "format":     "false",
        "file_system":"mkfs.ext4",
        "mount":      "/home",
        "device_use": "home"
    },
}

##############################################################################
# Utility: run_cmd
##############################################################################

def run_cmd(cmd):
    """
    Helper to run a shell command and return stdout on success.
    Raises SystemExit on error with the stderr message.
    """
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        raise SystemExit(f"Command failed: {cmd}")
    return result.stdout.strip()

##############################################################################
# List all disk-type devices with lsblk
##############################################################################

def list_all_block_devices():
    columns = ["NAME","MAJ:MIN","RM","SIZE","RO","TYPE","MOUNTPOINTS"]
    cmd = f"lsblk -rno {','.join(columns)}"
    output = run_cmd(cmd)

    rows = []
    for line in output.splitlines():
        parts = line.split(None, 6)
        if len(parts) < 6:
            continue
        name, maj_min, rm, size, ro, typ = parts[:6]
        mountpoint = parts[6] if len(parts) == 7 else ""
        rows.append([name, maj_min, rm, size, ro, typ, mountpoint])

    print("\n=== All Block Devices ===")
    print("NAME       MAJ:MIN RM  SIZE RO TYPE MOUNTPOINTS")
    for r in rows:
        print(" ".join(r))

    disks = []
    for row in rows:
        if row[5] == "disk":
            disks.append(f"/dev/{row[0]}")
    return disks

##############################################################################
# Prompt user which disk(s) to use, and how
##############################################################################

def guess_device_type(disk_path):
    if re.match(r"^/dev/sd[a-z]+$", disk_path):
        return "sd"
    if "nvme" in disk_path:
        return "nvme"
    return "other"

def prompt_device_usage(disks):
    """
    Example: returns something like
    [
      {
        "use_device": True,
        "device_use": "system",
        "device": "/dev/sda",
        "device_type": "sd"
      },
      {
        "use_device": True,
        "device_use": "home",
        "device": "/dev/nvme0n1",
        "device_type": "nvme"
      }
    ]
    """
    devices_dict = []
    for d in disks:
        dt = guess_device_type(d)
        print(f"\nDiscovered device: {d} ({dt})")
        ans = input("  Use this device for partitioning? (y/n): ").strip().lower()
        if ans not in ["y", "yes"]:
            devices_dict.append({
                "use_device": False,
                "device_use": None,
                "device": d,
                "device_type": dt
            })
            continue

        print("  How do you want to use this device?")
        print("   1) system")
        print("   2) home")
        print("   3) none (create partitions but no auto-mount?)")
        print("   4) custom (var, opt, store, etc.)")
        c = input("  Enter choice [1-4]: ").strip()
        if c == "1":
            device_use = "system"
        elif c == "2":
            device_use = "home"
        elif c == "3":
            device_use = "none"
        elif c == "4":
            device_use = input("    Enter custom label: ").strip() or "custom"
        else:
            device_use = "none"

        devices_dict.append({
            "use_device": True,
            "device_use": device_use,
            "device": d,
            "device_type": dt
        })

    return devices_dict

##############################################################################
# Build partition script lines
##############################################################################

def build_partition_script(devices_dict):
    """
    Based on devices_dict, find all DESIRED_PARTITIONS that match device_use.
    Generate parted commands to create them, plus optional mkfs + mount lines.

    We'll build a list of shell commands, then write them to 'partitioning.sh'.
    """
    script_lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        "# Generated partitioning script"
    ]

    for dev_info in devices_dict:
        if not dev_info["use_device"]:
            script_lines.append(f"# Skipping {dev_info['device']} (user chose not to use)")
            continue

        disk = dev_info["device"]
        usage = dev_info["device_use"]

        script_lines.append(f"\n# Partitioning for {disk} as {usage}")
        # Create a new GPT label (WARNING: this destroys existing data!)
        script_lines.append(f"parted -s {disk} mklabel gpt || true")

        # Track the start (in MiB). Real logic must detect existing partitions, etc.
        current_start = 1  # start at 1MiB
        part_number = 0

        # Sort by a known order if you want a certain order of creation
        # Or just iterate in dictionary order if you prefer
        for label, conf in DESIRED_PARTITIONS.items():
            # e.g. conf["device_use"] => "system" or "home"
            if conf.get("device_use", "none") != usage:
                continue  # not relevant for this device

            part_number += 1
            size = conf.get("size", None)  # might be "512MiB", "128GiB", or None
            ptype = conf["type"]  # e.g. "fat32", "ext4"

            # parted end
            if size:
                # We'll let parted do an expression: e.g. "1MiB + 512MiB"
                end_str = f"{current_start}MiB+{size}"
            else:
                # no size => use the rest of the disk
                end_str = "100%"

            # parted command to create partition
            script_lines.append(
                f"parted -s {disk} mkpart {label} {ptype} {current_start}MiB {end_str}"
            )

            # If it's EFI, we might want to set boot & esp flags
            if label.lower() == "efi":
                script_lines.append(f"parted -s {disk} set {part_number} boot on || true")
                script_lines.append(f"parted -s {disk} set {part_number} esp on || true")

            # parted name (optional, if parted supports naming)
            script_lines.append(f"parted -s {disk} name {part_number} {label}")

            # Update current_start if we used a numeric size
            if size:
                # We'll assume parted handles the expression for 'end'
                # but let's guess we can parse e.g. "512MiB" to an int
                # This is simplistic and doesn't handle '128GiB' properly
                # but for demonstration, we'll do a rough parse:
                num_match = re.match(r"^(\d+)", size)
                unit_match = re.match(r"^\d+(\w+)$", size)
                if num_match and unit_match:
                    length_value = int(num_match.group(1))
                    length_unit  = unit_match.group(1).lower()  # e.g. "mib", "gib"
                    if "g" in length_unit:
                        current_start += length_value * 1024
                    else:
                        # assume MiB
                        current_start += length_value
                else:
                    # If we can't parse, just cheat by 1MiB more
                    current_start += 1
            else:
                # used 100%
                pass

            # Check if "format" == "true" => add mkfs or mkswap
            do_format = str(conf.get("format", "false")).lower() in ["true", "yes"]
            fs_cmd = conf.get("file_system", "")  # e.g. "mkfs.ext4"
            if do_format and fs_cmd:
                if dev_info["device_type"] == "nvme":
                    part_dev = f"{disk}p{part_number}"
                else:
                    part_dev = f"{disk}{part_number}"
                script_lines.append(f"{fs_cmd} {part_dev}")

            # If there's a mount path, we can add mount commands
            mnt_path = conf.get("mount", "")
            if mnt_path:
                if dev_info["device_type"] == "nvme":
                    part_dev = f"{disk}p{part_number}"
                else:
                    part_dev = f"{disk}{part_number}"
                # Ensure the directory
                script_lines.append(f"mkdir -p {mnt_path}")
                script_lines.append(f"mount {part_dev} {mnt_path}")

        script_lines.append("")  # blank line

    return script_lines

##############################################################################
# MAIN
##############################################################################

def main():
    # 1) List all block devices
    disks = list_all_block_devices()
    if not disks:
        print("No disk devices found.")
        sys.exit(1)

    # 2) Prompt which to use + usage
    devices_dict = prompt_device_usage(disks)

    # 3) Build the partition script
    script_lines = build_partition_script(devices_dict)

    # 4) Write to a file
    script_path = "partitioning.sh"
    with open(script_path, "w") as f:
        for line in script_lines:
            f.write(line + "\n")

    os.chmod(script_path, 0o755)

    print(f"\nGenerated shell script: {script_path}")
    print("Review carefully, then run it if you want to proceed, e.g.:")
    print(f"  sudo ./{script_path}")

if __name__ == "__main__":
    main()
