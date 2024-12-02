import requests
import tempfile
import os
import tarfile
import zipfile
import shutil
import subprocess
import re
import time
import threading

class NgrokProxyManager:
    def __init__(self, ngrok_token):
        self.ngrok_token = ngrok_token
        self.ngrok_process = None
        self.proxy_process = None
        self.local_appdata = os.getenv('LOCALAPPDATA')
        self.ngrok_dir = os.path.join(self.local_appdata, 'Microsoft', 'Networking')
        self.proxy_dir = None
        self.ngrok_url = None

    def install_ngrok(self):
        # Install ngrok if not already installed
        if not os.path.exists(self.ngrok_dir):
            os.makedirs(self.ngrok_dir, exist_ok=True)

            r = requests.get(url='https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip')
            r.raise_for_status()
            zip_path = tempfile.NamedTemporaryFile(suffix='.zip', delete=False).name

            with open(zip_path, "wb") as f:
                f.write(r.content)

            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(self.ngrok_dir)

            os.remove(zip_path)

        self.ngrok_exe = os.path.join(self.ngrok_dir, 'ngrok.exe')

        # Configure ngrok with the provided authentication token
        subprocess.run([self.ngrok_exe, 'config', 'add-authtoken', self.ngrok_token], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def start_ngrok_tunnel(self):
        # Start ngrok tunnel
        self.ngrok_process = subprocess.Popen([self.ngrok_exe, 'tcp', '33080'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)
        
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

    def download_and_run_proxy(self):
        # Download the proxy-windows-amd64.tar.gz
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

        # Run proxy.exe http on localhost only to prevent firewall prompts
        proxy_exe = os.path.join(self.proxy_dir, 'proxy.exe')
        self.proxy_process = subprocess.Popen([proxy_exe, 'http', '-p', '127.0.0.1:8080', '--nolog'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)

    def start_all(self):
        # Install ngrok, start ngrok tunnel, and run the proxy
        self.install_ngrok()
        self.start_ngrok_tunnel()
        self.download_and_run_proxy()
        return self.ngrok_url

    def stop_all(self):
        # Terminate ngrok process
        if self.ngrok_process:
            self.ngrok_process.terminate()
            self.ngrok_process.wait()
            print("Ngrok process terminated.")

        # Terminate proxy process
        if self.proxy_process:
            self.proxy_process.terminate()
            self.proxy_process.wait()
            print("Proxy process terminated.")

        # Clean up the proxy directory
        if self.proxy_dir and os.path.exists(self.proxy_dir):
            shutil.rmtree(self.proxy_dir)
            print("Temporary proxy directory cleaned up.")

if __name__ == "__main__":
    # Example usage
    ngrok_token = '2IoD8A022Xb2l5bokyF4t1oX42d_26n6KRRjyas8EKYmf314a'  # Replace with your ngrok auth token
    manager = NgrokProxyManager(ngrok_token)
    try:
        ngrok_url = manager.start_all()
        print(f'Ngrok is running at: {ngrok_url}')
        input("Press Enter to stop all services...")
    finally:
        manager.stop_all()
