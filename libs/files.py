import os
import shutil

class FileManager:
    def __init__(self):
        self.current_directory = os.getcwd()  # Initialize with the current working directory

    def cd(self, path: str) -> str:
        try:
            os.chdir(path)
            self.current_directory = os.getcwd()
            return f"Directory changed to: {self.current_directory}"
        except FileNotFoundError:
            return f"Error: Directory '{path}' not found."
        except NotADirectoryError:
            return f"Error: '{path}' is not a directory."
        except PermissionError:
            return f"Error: Permission denied for '{path}'."

    def ls(self) -> str:
        try:
            files = os.listdir(self.current_directory)
            return "\n".join(files) if files else "No files or directories found."
        except PermissionError:
            return f"Error: Permission denied for '{self.current_directory}'."

    def move(self, source: str, destination: str) -> str:
        try:
            shutil.move(source, destination)
            return f"'{source}' moved to '{destination}'."
        except FileNotFoundError:
            return f"Error: '{source}' not found."
        except PermissionError:
            return f"Error: Permission denied for '{source}'."
        except Exception as e:
            return f"Error moving '{source}': {e}"

    def copy(self, source: str, destination: str) -> str:
        try:
            if os.path.isdir(source):
                shutil.copytree(source, destination)
            else:
                shutil.copy2(source, destination)
            return f"'{source}' copied to '{destination}'."
        except FileNotFoundError:
            return f"Error: '{source}' not found."
        except FileExistsError:
            return f"Error: '{destination}' already exists."
        except PermissionError:
            return f"Error: Permission denied for '{source}'."
        except Exception as e:
            return f"Error copying '{source}': {e}"

    def delete(self, path: str) -> str:
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            return f"'{path}' deleted successfully."
        except FileNotFoundError:
            return f"Error: '{path}' not found."
        except PermissionError:
            return f"Error: Permission denied for '{path}'."
        except Exception as e:
            return f"Error deleting '{path}': {e}"

    def mkdir(self, path: str) -> str:
        try:
            os.makedirs(path, exist_ok=True)
            return f"Directory '{path}' created successfully."
        except PermissionError:
            return f"Error: Permission denied for '{path}'."
        except Exception as e:
            return f"Error creating directory '{path}': {e}"
