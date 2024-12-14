import json
import redis
import requests
import asyncio
from datetime import datetime, timezone
import logging
import os
import re
import tkinter as tk
from tkinter import messagebox
from threading import Thread

# Define the Tkinter application class
class RedisTelegramApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Redis Telegram Manager")

        # Input fields for TELEGRAM_TOKEN and REDIS_CLI_COMMAND
        tk.Label(root, text="Telegram Token:").grid(row=0, column=0, padx=10, pady=5)
        self.telegram_token_entry = tk.Entry(root, width=50)
        self.telegram_token_entry.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(root, text="Redis CLI Command:").grid(row=1, column=0, padx=10, pady=5)
        self.redis_cli_entry = tk.Entry(root, width=50)
        self.redis_cli_entry.grid(row=1, column=1, padx=10, pady=5)

        # Start and Stop buttons
        self.start_button = tk.Button(root, text="Start", command=self.start_script)
        self.start_button.grid(row=2, column=0, padx=10, pady=10)

        self.stop_button = tk.Button(root, text="Stop", command=self.stop_script, state=tk.DISABLED)
        self.stop_button.grid(row=2, column=1, padx=10, pady=10)

        self.running = False
        self.telegram_bot_token = None
        self.redis_cli_command = None
        self.loop = None

    def start_script(self):
        self.telegram_bot_token = self.telegram_token_entry.get()
        self.redis_cli_command = self.redis_cli_entry.get()

        if not self.telegram_bot_token or not self.redis_cli_command:
            messagebox.showerror("Error", "Both fields are required!")
            return

        self.running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)

        # Start the asyncio loop in a separate thread
        Thread(target=self.run_asyncio_loop, daemon=True).start()

    def stop_script(self):
        self.running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)

    def run_asyncio_loop(self):
        asyncio.run(self.main())

    async def main(self):
        logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
        logging.info("Starting Telegram Redis Manager...")

        redis_config = parse_redis_url(self.redis_cli_command)
        if not redis_config:
            logging.error("Invalid REDIS_CLI_COMMAND format.")
            messagebox.showerror("Error", "Invalid REDIS_CLI_COMMAND format.")
            self.stop_script()
            return

        global redis_client
        try:
            redis_client = redis.Redis(
                host=redis_config['host'],
                port=redis_config['port'],
                password=redis_config['password'],
                decode_responses=True
            )
            logging.info("Connected to Redis.")
        except redis.RedisError as e:
            logging.error(f"Redis connection error: {e}")
            messagebox.showerror("Error", f"Redis connection error: {e}")
            self.stop_script()
            return

        global TELEGRAM_API_URL
        TELEGRAM_API_URL = f"https://api.telegram.org/bot{self.telegram_bot_token}"

        self.loop = asyncio.get_event_loop()
        await asyncio.gather(self.fetch_telegram_updates(), self.clear_redis_periodically())

    async def fetch_telegram_updates(self):
        offset = 0
        while self.running:
            try:
                logging.debug("Fetching Telegram updates...")
                response = requests.get(f"{TELEGRAM_API_URL}/getUpdates", params={"offset": offset, "timeout": 30})
                updates = response.json()
                logging.debug(f"Updates received: {updates}")
                if updates.get("ok"):
                    for update in updates["result"]:
                        offset = update["update_id"] + 1
                        process_telegram_update(update)
            except requests.RequestException as e:
                logging.error(f"Error fetching Telegram updates: {e}")
            await asyncio.sleep(1)

    async def clear_redis_periodically(self):
        logging.info("Clearing old Redis data...")
        redis_client.delete(REDIS_COMMAND_CHANNEL)
        redis_client.delete(REDIS_STATUS_CHANNEL)

        while self.running:
            await asyncio.sleep(30)
            redis_client.delete(REDIS_COMMAND_CHANNEL)
            redis_client.delete(REDIS_STATUS_CHANNEL)
            logging.debug("Redis channels cleared.")

# Helper Functions
def parse_redis_url(command):
    try:
        cli_pattern = r'redis-cli\s+-u\s+(redis://[^\s]+)'
        cli_match = re.match(cli_pattern, command)

        if not cli_match:
            return None

        redis_url = cli_match.group(1)

        url_pattern = r'redis://([^:]+):([^@]+)@([^:]+):(\d+)'
        url_match = re.match(url_pattern, redis_url)

        if url_match:
            return {
                "host": url_match.group(3),
                "password": url_match.group(2),
                "port": int(url_match.group(4)),
            }
        else:
            return None
    except Exception as e:
        logging.error(f"Error parsing Redis CLI command: {e}")
        return None

def process_telegram_update(update):
    global redis_client
    logging.debug(f"Processing Telegram update: {update}")

    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"].get("text", "")

        logging.info(f"Received message: {text} from chat_id: {chat_id}")

        if text == "/list_computers":
            list_computers(chat_id)
        elif text.startswith("/set_computer"):
            try:
                _, computer_id = text.split(maxsplit=1)
                set_computer(chat_id, computer_id)
            except ValueError:
                logging.warning("Invalid /set_computer command format.")
                send_telegram_message(chat_id, "Usage: /set_computer <COMPUTER_ID>")
        else:
            forward_command(chat_id, text)

def list_computers(chat_id):
    logging.debug("Listing all connected computers.")
    computers = redis_client.hgetall(REDIS_STATUS_CHANNEL)
    now = datetime.now(timezone.utc)
    online_computers = []

    if not computers:
        logging.info("No computers are registered in Redis.")
        send_telegram_message(chat_id, "No computers are currently online.")
        return

    for comp_id, last_seen in computers.items():
        try:
            last_seen_time = datetime.fromisoformat(last_seen).replace(tzinfo=timezone.utc)
        except ValueError:
            try:
                last_seen_time = datetime.fromtimestamp(float(last_seen)).replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                logging.warning(f"Invalid timestamp for computer {comp_id}: {last_seen}")
                online_computers.append(f"{comp_id} (Online)")
                continue

        time_diff = (now - last_seen_time).total_seconds()
        if time_diff < 30:
            online_computers.append(f"{comp_id} (Online)")

    if online_computers:
        message = "Connected Computers:\n" + "\n".join(online_computers)
    else:
        message = "No computers are currently online."

    logging.info(f"Sending list of computers to chat_id: {chat_id}")
    send_telegram_message(chat_id, message)

def set_computer(chat_id, computer_id):
    global redis_client
    global selected_computer
    logging.debug(f"Setting selected computer to: {computer_id}")

    try:
        computers = redis_client.hgetall(REDIS_STATUS_CHANNEL)
        if computer_id in computers:
            selected_computer = computer_id
            redis_client.set("current_computer", computer_id)
            send_telegram_message(chat_id, f"Selected computer: {computer_id}")
        else:
            send_telegram_message(chat_id, f"Computer ID {computer_id} not found.")
    except redis.RedisError as e:
        logging.error(f"Error accessing Redis: {e}")
        send_telegram_message(chat_id, "Error setting computer.")

def forward_command(chat_id, text):
    global redis_client
    global selected_computer
    logging.debug(f"Forwarding command: {text} to selected computer: {selected_computer}")

    if not selected_computer:
        send_telegram_message(chat_id, "No computer selected. Use /set_computer <COMPUTER_ID> first.")
        return

    try:
        command = json.dumps({
            "target": selected_computer,
            "chat_id": chat_id,
            "command": text
        })
        redis_client.publish(REDIS_COMMAND_CHANNEL, command)
        logging.info(f"Command sent to computer {selected_computer}: {text}")
    except redis.RedisError as e:
        logging.error(f"Error publishing command to Redis: {e}")
        send_telegram_message(chat_id, "Error forwarding command.")

def send_telegram_message(chat_id, text):
    global TELEGRAM_API_URL
    logging.debug(f"Sending message to chat_id {chat_id}: {text}")
    try:
        payload = {"chat_id": chat_id, "text": text}
        response = requests.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload)
        logging.debug(f"Telegram API response: {response.json()}")
    except requests.RequestException as e:
        logging.error(f"Error sending Telegram message: {e}")

# Constants for Redis channels
REDIS_COMMAND_CHANNEL = "commands"
REDIS_STATUS_CHANNEL = "status"
selected_computer = None

if __name__ == "__main__":
    root = tk.Tk()
    app = RedisTelegramApp(root)
    root.mainloop()
