import os
import subprocess



# Path to the hosts file
hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
redirect_ip = "127.0.0.1"

def block_domains(domains):


    
    """
    Blocks a list of domains by adding them to the hosts file.
    
    :param domains: List of domains to block.
    """
    try:
        # Check for administrative privileges
        if not os.access(hosts_path, os.W_OK):
            raise PermissionError("This script needs to be run as an administrator.")

        with open(hosts_path, "r") as file:
            lines = file.readlines()

        with open(hosts_path, "a") as file:
            for domain in domains:
                if not any(domain in line for line in lines):
                    file.write(f"{redirect_ip} {domain}\n")
                    print(f"Blocked: {domain}")
                else:
                    print(f"Already blocked: {domain}")

        # Flush DNS cache
        flush_dns()

    except PermissionError as e:
        print(e)
        print("Please run this script as an administrator.")
    except Exception as e:
        print(f"An error occurred: {e}")


def unblock_domains(domains):
    """
    Unblocks a list of domains by removing them from the hosts file.
    
    :param domains: List of domains to unblock.
    """
    try:
        if not os.access(hosts_path, os.W_OK):
            raise PermissionError("This script needs to be run as an administrator.")

        with open(hosts_path, "r") as file:
            lines = file.readlines()

        with open(hosts_path, "w") as file:
            for line in lines:
                if not any(domain in line for domain in domains):
                    file.write(line)
                else:
                    print(f"Unblocked: {line.strip().split()[-1]}")

        # Flush DNS cache
        flush_dns()

    except PermissionError as e:
        print(e)
        print("Please run this script as an administrator.")
    except Exception as e:
        print(f"An error occurred: {e}")


def flush_dns():
    """
    Flushes the DNS cache by executing the `ipconfig /flushdns` command.
    """
    try:
        result = subprocess.run(["ipconfig", "/flushdns"], capture_output=True, text=True)
        if result.returncode == 0:
            print("DNS cache successfully flushed.")
        else:
            print(f"Failed to flush DNS cache: {result.stderr}")
    except Exception as e:
        print(f"An error occurred while flushing DNS: {e}")


