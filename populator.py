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
    logging.debug(f"Processing Telegram update: {update}")
    # Implementation remains the same as original script

# Constants for Redis channels
REDIS_COMMAND_CHANNEL = "commands"
REDIS_STATUS_CHANNEL = "status"

if __name__ == "__main__":
    root = tk.Tk()
    app = RedisTelegramApp(root)
    root.mainloop()
