import subprocess
import tempfile
import os

class ProcessManager:
    def list_processes(self) -> str:
        try:
            result = subprocess.run(["tasklist"], capture_output=True, text=True, shell=True)
            if result.returncode != 0:
                return f"Error retrieving process list: {result.stderr.strip()}"
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w")
            temp_file.write(result.stdout)
            temp_file.close()
            return temp_file.name
        except Exception as e:
            return f"Error listing processes: {e}"

    def kill_process_by_pid(self, pid: int) -> str:
        try:
            result = subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, text=True, shell=True)
            if result.returncode != 0:
                return f"Error killing process with PID {pid}: {result.stderr.strip()}"
            return f"Successfully killed process with PID {pid}."
        except Exception as e:
            return f"Error killing process with PID {pid}: {e}"

    def kill_process_by_name(self, name: str) -> str:
        try:
            result = subprocess.run(["taskkill", "/IM", name, "/F"], capture_output=True, text=True, shell=True)
            if result.returncode != 0:
                return f"Error killing process '{name}': {result.stderr.strip()}"
            return f"Successfully killed all instances of '{name}'."
        except Exception as e:
            return f"Error killing process '{name}': {e}"
