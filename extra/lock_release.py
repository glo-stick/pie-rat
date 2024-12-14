'''I fully made this with ChatGPT, but it is for debugging anyway'''

import redis

# Redis connection configuration
REDIS_HOST = ""
REDIS_PORT = 000
REDIS_PASS = ""

# Define lock key pattern
LOCK_KEY_PATTERN = "computer_lock:*"

def release_all_locks():
    """
    Manually release all locks by deleting Redis keys matching the lock pattern.
    """
    try:
        # Connect to Redis
        redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASS,
            decode_responses=True
        )
        print("Connected to Redis.")

        # Find all keys matching the lock pattern
        lock_keys = redis_client.keys(LOCK_KEY_PATTERN)
        if not lock_keys:
            print("No lock keys found.")
            return

        # Delete the lock keys
        for key in lock_keys:
            redis_client.delete(key)
            print(f"Deleted lock key: {key}")

        print("All locks released successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to release locks: {e}")

if __name__ == "__main__":
    release_all_locks()
