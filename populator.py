import json
import redis
import requests
import asyncio
from datetime import datetime, timezone
import logging
import os
import re

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



# Set up logging
logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s - %(levelname)s - %(message)s")

# TELEGRAM CONF
TELEGRAM_BOT_TOKEN = str(os.getenv('TELEGRAM_TOKEN'))

# REDIS CLI CONF
REDIS_CLI_COMMAND = str(os.getenv('REDIS_CLI_COMMAND'))
redis_config = parse_redis_url(REDIS_CLI_COMMAND)
if not redis_config:
    logging.error("Invalid REDIS_CLI_COMMAND environment variable format.")
    raise ValueError("Invalid REDIS_CLI_COMMAND format.")

REDIS_HOST = redis_config['host']
REDIS_PORT = redis_config['port']
REDIS_PASSWORD = redis_config['password']

# Redis connection
try:
    redis_client = redis.Redis(host=REDIS_HOST,
                               port=REDIS_PORT,
                               password=REDIS_PASSWORD,
                               decode_responses=True)
    logging.info("Connected to Redis.")
except redis.RedisError as e:
    logging.error(f"Redis connection error: {e}")
    raise

selected_computer = None
REDIS_COMMAND_CHANNEL = "commands"
REDIS_STATUS_CHANNEL = "status"

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


async def fetch_telegram_updates():
    offset = 0
    while True:
        try:
            logging.debug("Fetching Telegram updates...")
            response = requests.get(f"{TELEGRAM_API_URL}/getUpdates",
                                    params={"offset": offset, "timeout": 30})
            updates = response.json()
            logging.debug(f"Updates received: {updates}")
            if updates.get("ok"):
                for update in updates["result"]:
                    offset = update["update_id"] + 1
                    process_telegram_update(update)
        except requests.RequestException as e:
            logging.error(f"Error fetching Telegram updates: {e}")
        await asyncio.sleep(1)


def process_telegram_update(update):
    global selected_computer
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
    logging.debug(f"Sending message to chat_id {chat_id}: {text}")
    try:
        payload = {"chat_id": chat_id, "text": text}
        response = requests.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload)
        logging.debug(f"Telegram API response: {response.json()}")
    except requests.RequestException as e:
        logging.error(f"Error sending Telegram message: {e}")


async def clear_redis_periodically():
    logging.info("Clearing old Redis data...")
    redis_client.delete(REDIS_COMMAND_CHANNEL)
    redis_client.delete(REDIS_STATUS_CHANNEL)

    while True:
        await asyncio.sleep(30)
        redis_client.delete(REDIS_COMMAND_CHANNEL)
        redis_client.delete(REDIS_STATUS_CHANNEL)
        logging.debug("Redis channels cleared.")


async def main():
    logging.info("Central Redis Pusher Script is running...")
    await asyncio.gather(fetch_telegram_updates(), clear_redis_periodically())


if __name__ == "__main__":
    asyncio.run(main())
