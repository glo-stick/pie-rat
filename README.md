
# PieRat
**Yet another multi session Windows RAT for administrating multiple clients via a Telegram bot.**
---
[![](https://dcbadge.limes.pink/api/server/u5VkfQ8Ehj)](https://discord.gg/u5VkfQ8Ehj)
![](https://dcbadge.limes.pink/api/shield/1312773204032487445)
---


### Disclaimer
> This project was made for **educational purposes** as a side project. I do not condone or support any malicious activity involving this tool. Use responsibly and ethically.
>
> - **No Support:** I will not provide installation support or a tutorial on setting up Redis Cloud to prevent misuse.
> - **No Liability:** I am not responsible for any damages caused by the use of this tool.

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
  - `/cd`, `/pwd`, `/ls`, `/move`, `/copy`, `/delete`, `/mkdir`
- **Process Management**:
  - `/ps` - List processes.
  - `/pskill <PID or PROCESS NAME>` - Kill a process.

---

### Fun
- **Message Box**: Display a message box on the target machine.
  - `/msg_box "TITLE" "CONTENT"`
- **Jumpscare**: Play loud and frightening videos.
  - `/jumpscare <PRESET>`
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
  - `/start_keylogger`, `/stop_keylogger`
- **Proxy**: Host a proxy with ngrok.
  - `/start_proxy`, `/stop_proxy`
- **DNS Poisoner**: Block or unblock domains, including AV sites.
  - `/block_av`, `/unblock_av`
  - `/block_domain <DOMAIN>`, `/unblock_domain <DOMAIN>`
- **Ransomware**: On demand encryption and decryption with Fernet.
  - `/set_key <KEY>`, `/encrypt_files`, `/decrypt_files`



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


## Installation

Check the [wiki](https://github.com/glo-stick/pie-rat/wiki/Installation)

---

## Usage

1. Compile ```main.py``` with your favourite compiler, e.g ```pyinstaller``` ```nuitka```
2. Run ```populator.py``` in the background of your computer.
3. Deploy the main.py executable to target machine.
4. On the Telegram Bot send ```/list_computers``` to list computers connected and ```/set_computer <COMPUTER_ID>``` to channel commands into that computer

---

## How it works.

The system operates with the ```populator.py``` script, which serves as the single poller to fetch Telegram updates and populate them into the Redis server. This approach addresses the limitation of a single bot instance being allowed to poll updates by centralizing the process through ```populator.py```. This script is only required to run while interacting with the bot. Worker processes, referred to as "zombies," connect to the Redis server to retrieve and process updates, reducing load and bypassing polling restrictions. Zombies handle tasks based on their assigned roles, reacting to updates accordingly. The Redis server also manages the assignment of specific computers by comparing their UUIDs with preconfigured values that are set in the Redis. Additionally, ```populator.py``` processes global commands, such as ```/list_computers``` and ```/set_computer```



## Acknowledgements

- ChatGPT, helped me in some of the minor things / bugs.
- Pysilon, inspired me to make this.
