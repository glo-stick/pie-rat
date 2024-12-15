
# PieRat
**Yet another multi session Windows RAT for administrating multiple clients via a Telegram bot.**
---
[![](https://dcbadge.limes.pink/api/server/u5VkfQ8Ehj)](https://discord.gg/u5VkfQ8Ehj)
![](https://dcbadge.limes.pink/api/shield/1312773204032487445)
![GitHub commit activity](https://img.shields.io/github/commit-activity/t/glo-stick/pie-rat)

---


### Disclaimer
> This project was made for **educational purposes** as a side project. I do not condone or support any malicious activity involving this tool. Use responsibly and ethically.

---

## Features / Commands

### General
- **File Management**: Upload and download files via Telegram.
  - `/upload` - Prompts for a file to upload to the chat.
  - `/download` - Downloads files.
- **Shell Commands**: Execute shell commands remotely.
  - `/execute <SHELL_COMMAND>`
- **System Info**: View system details.
  - `/sys_info`
- **Screenshot**: Take a screenshot of the target machine.
  - `/screenshot`
- **File Management Commands**:
  - `/cd` - Change the current directory.
  - `/pwd` - Display the current working directory.
  - `/ls` - List files and directories in the current directory.
  - `/move <SOURCE> <DESTINATION>` - Move or rename a file/directory.
  - `/copy <SOURCE> <DESTINATION>` - Copy a file or directory.
  - `/delete <PATH>` - Delete a file or directory.
  - `/mkdir <DIRECTORY_NAME>` - Create a new directory.
- **Process Management**:
  - `/ps` - List processes.
  - `/pskill <PID or PROCESS NAME>` - Kill a process.

---

### Fun
- **Message Box**: Display a message box on the target machine.
  - `/msg_box "TITLE" "CONTENT"`
- **Jumpscare**: Play loud and frightening videos.
  - `/jumpscare <PRESET (jeff_jumpscare)>` 
- **Volume Control**:
  - `/get_volume` - Get current volume.
  - `/set_volume <INT>` - Set system volume.
- **Audio Player**:
  - `/start_audio <LOCAL_AUDIO_PATH>` - Play audio on the target.
  - `/stop_audio` - Stop audio playback.
- **Text-to-Speech**: Speak text on the target machine.
  - `/tts <TEXT TO SPEAK>`
- **Open URL**: Launch a URL in the default browser.
  - `/open_url <URL>`

---

### Other
- **Keylogger**: Start or stop keylogging.
  - `/start_keylogger` - Start keylogging.
  - `/stop_keylogger` - Stop keylogging and retrieve logs.
- **Proxy**: Host a proxy with ngrok.
  - `/start_proxy` - Start a proxy using ngrok.
  - `/stop_proxy` - Stop the active proxy.
- **DNS Poisoner**: Block or unblock domains, including AV sites.
  - `/block_av` - Block common antivirus domains.
  - `/unblock_av` - Unblock common antivirus domains.
  - `/block_domain <DOMAIN>` - Block a specific domain.
  - `/unblock_domain <DOMAIN>` - Unblock a specific domain.
- **Ransomware**: On demand encryption and decryption with Fernet.
  - `/set_key <KEY>` - Set the encryption key.
  - `/encrypt_files` - Encrypt files in the target system.
  - `/decrypt_files` - Decrypt files in the target system.

---

### Persistence
- **List Methods**: View available persistence methods.
  - `/list_persistence_methods` - List all supported persistence methods with descriptions.
- **Apply Persistence**: Apply a specific persistence method.
  - `/apply_persistence <METHOD> [STEALTH_NAME] [KEY_NAME]` - Apply persistence using the specified method.
- **Help**: Get detailed help on a specific persistence method.
  - `/persistence_help <METHOD>` - Show detailed help for a persistence method.

---

### Modules (Auto-Installable)
Modules are precompiled and hosted to save payload space.

#### Camera Module
- **List Cameras**: `/list_cameras`
- **Capture Webcam**: `/capture_webcam <INDEX>`

---

# Screenshots
---
![screenshot](https://raw.githubusercontent.com/glo-stick/pie-rat/refs/heads/main/photos/computers.png)
---
![screenshot](https://raw.githubusercontent.com/glo-stick/pie-rat/refs/heads/main/photos/sysinfo.png)
---
![screenshot](https://raw.githubusercontent.com/glo-stick/pie-rat/refs/heads/main/photos/screenshot.png)
---
![screenshot](https://raw.githubusercontent.com/glo-stick/pie-rat/refs/heads/main/photos/msg.png)
---


## Installation and Usage

Check the [wiki](https://github.com/glo-stick/pie-rat/wiki/Installation)

---


## How it works.

The system operates with the ```populator.py``` script, which serves as the single poller to fetch Telegram updates and populate them into the Redis server. This approach addresses the limitation of a single bot instance being allowed to poll updates by centralizing the process through ```populator.py```. This script is only required to run while interacting with the bot. Worker processes, referred to as "zombies," connect to the Redis server to retrieve and process updates, reducing load and bypassing polling restrictions. Zombies handle tasks based on their assigned roles, reacting to updates accordingly. The Redis server also manages the assignment of specific computers by comparing their UUIDs with preconfigured values that are set in the Redis. Additionally, ```populator.py``` processes global commands, such as ```/list_computers``` and ```/set_computer```



## Acknowledgements

- ChatGPT, helped me in some of the minor things / bugs.
- Pysilon, inspired me to make this.
