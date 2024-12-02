import json
import redis
import requests
import asyncio
from datetime import datetime, timezone

# TELEGRAM CONF
TELEGRAM_BOT_TOKEN = ""


#REDIS CONF
REDIS_HOST = ""
REDIS_PORT = 0000 #PORT GOES HERE
REDIS_PASSWORD = ""


# Redis connection
redis_client = redis.Redis(
    host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD, decode_responses=True
)

selected_computer = None  # To track the currently selected computer
REDIS_COMMAND_CHANNEL = "commands"
REDIS_STATUS_CHANNEL = "status"

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


async def fetch_telegram_updates():
    """Fetch updates from the Telegram bot."""
    offset = 0
    while True:
        try:
            response = requests.get(
                f"{TELEGRAM_API_URL}/getUpdates", params={"offset": offset, "timeout": 30}
            )
            updates = response.json()
            if updates.get("ok"):
                for update in updates["result"]:
                    offset = update["update_id"] + 1
                    process_telegram_update(update)
        except requests.RequestException as e:
            print(f"Error fetching Telegram updates: {e}")
        await asyncio.sleep(1)


def process_telegram_update(update):
    """Process a Telegram update and push commands to Redis."""
    global selected_computer

    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"].get("text", "")

        if text == "/list_computers":
            list_computers(chat_id)
        elif text.startswith("/set_computer"):
            try:
                _, computer_id = text.split(maxsplit=1)
                set_computer(chat_id, computer_id)
            except ValueError:
                send_telegram_message(chat_id, "Usage: /set_computer <COMPUTER_ID>")
        else:
            forward_command(chat_id, text)


def list_computers(chat_id):
    """List all connected computers."""
    computers = redis_client.hgetall(REDIS_STATUS_CHANNEL)
    now = datetime.now(timezone.utc)  # Current time in UTC
    online_computers = []

    for comp_id, last_seen in computers.items():
        try:
            # Parse as ISO 8601 timestamp
            last_seen_time = datetime.fromisoformat(last_seen).replace(tzinfo=timezone.utc)
        except ValueError:
            try:
                # Parse as Unix timestamp
                last_seen_time = datetime.fromtimestamp(datetime.timezone.utc)(float(last_seen)).replace(tzinfo=timezone.utc)
            except ValueError:
                online_computers.append(f"{comp_id} (Invalid timestamp)")
                continue

        # Calculate the time difference
        time_diff = (now - last_seen_time).total_seconds()
        if time_diff < 15:  # Active in the last 15 seconds
            online_computers.append(f"{comp_id} (Last seen: {int(time_diff)} seconds ago)")

    if online_computers:
        message = "Connected Computers:\n" + "\n".join(online_computers)
    else:
        message = "No computers are currently online."

    send_telegram_message(chat_id, message)


def set_computer(chat_id, computer_id):
    """Set the target computer for commands and save it in Redis."""
    global selected_computer

    try:
        computers = redis_client.hgetall(REDIS_STATUS_CHANNEL)  # Retrieve all registered computers
        if computer_id in computers:  # Check if the specified computer exists
            selected_computer = computer_id
            redis_client.set("current_computer", computer_id)  # Save the selected computer in Redis
            send_telegram_message(chat_id, f"Selected computer: {computer_id}")
        else:
            send_telegram_message(chat_id, f"Computer ID {computer_id} not found.")
    except redis.RedisError as e:
        print(f"Error accessing Redis: {e}")
        send_telegram_message(chat_id, "Error setting computer.")


def forward_command(chat_id, text):
    """Forward any command to the selected computer."""
    global selected_computer

    if not selected_computer:
        send_telegram_message(chat_id, "No computer selected. Use /set_computer <COMPUTER_ID> first.")
        return

    try:
        command = json.dumps({"target": selected_computer, "chat_id": chat_id, "command": text})
        redis_client.publish(REDIS_COMMAND_CHANNEL, command)
        print(f"Command sent to computer {selected_computer}.")
    except redis.RedisError as e:
        print(f"Error publishing command to Redis: {e}")
        send_telegram_message(chat_id, "Error forwarding command.")


def send_telegram_message(chat_id, text):
    """Send a message via Telegram."""
    try:
        payload = {"chat_id": chat_id, "text": text}
        requests.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload)
    except requests.RequestException as e:
        print(f"Error sending Telegram message: {e}")


async def clear_redis_periodically():
    """Clear Redis updates periodically or at startup."""
    print("Clearing old Redis data...")
    redis_client.delete(REDIS_COMMAND_CHANNEL)
    redis_client.delete(REDIS_STATUS_CHANNEL)

    while True:
        await asyncio.sleep(30)  # Every 30 Seconds
        redis_client.delete(REDIS_COMMAND_CHANNEL)
        redis_client.delete(REDIS_STATUS_CHANNEL)


async def main():
    """Main entry point."""
    print("Central Redis Pusher Script is running...")
    await asyncio.gather(fetch_telegram_updates(), clear_redis_periodically())


if __name__ == "__main__":
    asyncio.run(main())
