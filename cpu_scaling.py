#!/usr/bin/env python3

import argparse
import enum
import subprocess
import json
import sys
from pathlib import Path

class GovMode(enum.Enum):
    performance = "performance"
    powersave = "powersave"
    userspace = "userspace"
    ondemand = "ondemand"
    conservative = "conservative"
    schedutil = "schedutil"

def parse_args():
    parser = argparse.ArgumentParser(
        description="Disable and re-enable CPU Scaling on Linux, for eg: consistent code benchmarking")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--enable", action="store_true",
                    help="Enable CPU scaling")
    group.add_argument("--disable", action="store_true",
                    help="Disable CPU scaling")
    parser.add_argument("--mode", type=str, choices=[m.value for m in GovMode],
                    help="CPU frequency governor mode to use, leave blank for settings before disabled")
    return parser.parse_args()

def set_cpu_governor_mode(mode: GovMode, n_cpu: int = None):
    if mode not in get_supported_settings():
        sys.exit(f"specified mode {mode} not supported by CPU!")
    else:
        if n_cpu is not None:
            print(f"set CPU {n_cpu} to: {mode}")
            subprocess.run(["sudo", "cpupower", "--cpu", f"{n_cpu}",
                            "frequency-set", "-g", f"{mode}"],
                            capture_output=True, text=True, check=True)
        else:
            print(f"set all CPUs to mode {mode}")
            subprocess.run(["sudo", "cpupower", "frequency-set",
                            "-g", f"{mode}"],
                            capture_output=True, text=True, check=True)

def get_current_settings():
    """
    Get current CPU core freq governor settings as list of cpu->setting strings
    (index of list is 0-indexed CPU number)
    """
    out = subprocess.run(["sudo", "cpupower", "frequency-info", "-o", "proc"],
                         capture_output=True, text=True, check=True).stdout
    return [line.split()[-1] for line in out.splitlines()[1:]]

def get_supported_settings():
    """
    Sanity check list of supported settings for CPU model
    """
    out = subprocess.run(["sudo", "cat", 
                          "/sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors"],
                         capture_output=True, text=True, check=True).stdout
    return [line.split() for line in out.splitlines()][0]

def save_current_settings(fpath: Path):
    print(f"saving current scaling settings to file {str(fpath)}")
    with fpath.open("w") as f:
        json.dump(get_current_settings(), f, indent=4)

def recall_current_settings(fpath: Path):
    if not fpath.exists():
        sys.exit(f"error! no previous settings found at {str(fpath)}")
    else:
        with fpath.open() as f:
            settings = json.load(f)
            for n_cpu, setting in enumerate(settings):
                set_cpu_governor_mode(setting, n_cpu)
                
def main():
    args = parse_args()

    RESTORE_PATH = Path(__file__).parent / "previous_cpu_scaling.json"
    if args.disable:
        print("disabling CPU scaling, locking all cores to max CPU frequency")
        save_current_settings(RESTORE_PATH)
        set_cpu_governor_mode("performance")
    elif args.enable:
        print("enabling CPU scaling")
        if args.mode:
            mode = args.mode
            set_cpu_governor_mode(mode)
        else:
            print("recalling previous CPU core settings")
            recall_current_settings(RESTORE_PATH)

if __name__ == "__main__":
    main()
