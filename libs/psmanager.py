import subprocess
import tempfile
import os

class ProcessManager:
    def __init__(self):
        pass

    def list_processes(self) -> str:
        """
        List all running processes using tasklist and save to a temporary file.
        :return: Path to the temporary file or an error message.
        """
        try:
            # Run tasklist command to get the list of processes
            result = subprocess.run(["tasklist"], capture_output=True, text=True, shell=True)

            if result.returncode != 0:
                return f"Error retrieving process list: {result.stderr.strip()}"

            # Create a temporary file to store the process list
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w")
            temp_file.write(result.stdout)
            temp_file.close()

            return temp_file.name  # Return the temporary file's path
        except Exception as e:
            return f"Error listing processes: {e}"

    def kill_process_by_pid(self, pid: int) -> str:
        """
        Kill a process by PID.
        :param pid: Process ID to kill.
        :return: Success or error message.
        """
        try:
            result = subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, text=True, shell=True)

            if result.returncode != 0:
                return f"Error killing process with PID {pid}: {result.stderr.strip()}"

            return f"Successfully killed process with PID {pid}."
        except Exception as e:
            return f"Error killing process with PID {pid}: {e}"

    def kill_process_by_name(self, name: str) -> str:
        """
        Kill all processes by name.
        :param name: Name of the process to kill (e.g., notepad.exe).
        :return: Success or error message.
        """
        try:
            result = subprocess.run(["taskkill", "/IM", name, "/F"], capture_output=True, text=True, shell=True)

            if result.returncode != 0:
                return f"Error killing process '{name}': {result.stderr.strip()}"

            return f"Successfully killed all instances of '{name}'."
        except Exception as e:
            return f"Error killing process '{name}': {e}"
