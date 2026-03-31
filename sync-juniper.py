import paramiko
import time
import subprocess

# Juniper device configuration
MASTER = {
    "host": "192.168.100.21",
    "username": "user",
    "password": "password123"
}
BACKUP = {
    "host": "192.168.100.22",
    "username": "user",
    "password": "password123"
}

# Mandatory configuration
MANDATORY_CONFIG = """
system {
    host-name RO-BACKUP;
    root-authentication {
        encrypted-password "$adwadwawdsdahkiuwal; ## SECRET-DATA
    }
    login {
        user admin {
            uid 2000;
            class super-user;
            authentication {
                encrypted-password "$1$ydwaf/afawra0"; ## SECRET-DATA
            }
        }
    }
    services {
        ssh;
    }
    syslog {
        user * {
            any emergency;
        }
        file messages {
            any notice;
            authorization info;
        }
        file interactive-commands {
            interactive-commands any;
        }
    }
}
interfaces {
    ge-0/0/0 {
        unit 0 {
            family inet {
                address 192.168.100.22/24;
            }
        }
    }
}
routing-options {
    static {
        route 0.0.0.0/0 next-hop 192.168.100.1;
    }
}
"""

def ssh_command(device, command):
    """Execute an SSH command and return the output."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(device["host"], username=device["username"], password=device["password"], timeout=10)
        stdin, stdout, stderr = client.exec_command(command)
        output = stdout.read().decode("utf-8")
        client.close()
        return output
    except Exception as e:
        print(f"❌ ERROR: Failed to connect to {device['host']}: {e}")
        return None

def filter_config(config):
    """Remove hostname and interface ge-0/0/0 from the Master configuration."""
    new_config = []
    skip_block = False
    brace_count = 0

    for line in config.splitlines():
        if line.strip().startswith("host-name"):
            continue
        if "ge-0/0/0" in line:
            skip_block = True
            brace_count += line.count("{") - line.count("}")
        elif skip_block:
            brace_count += line.count("{") - line.count("}")
            if brace_count <= 0:
                skip_block = False
            continue

        if not skip_block:
            new_config.append(line)
    
    return "\n".join(new_config)

def validate_config(config):
    """Validate the configuration format before sending it to the device."""
    open_braces = config.count("{")
    close_braces = config.count("}")
    
    if open_braces != close_braces:
        print(f"❌ ERROR: Configuration braces are not properly closed! {open_braces} '{'{'}' vs {close_braces} '{'}'}'")
        return False
    
    return True

def sync_config():
    """Synchronize configuration from Master to Backup using `load override`."""
    print("📥 Fetching configuration from Master...")
    master_config = ssh_command(MASTER, "show configuration | no-more")

    if not master_config:
        print("❌ Failed to fetch configuration from Master.")
        return

    # Filter out interface ge-0/0/0 and hostname
    filtered_config = filter_config(master_config)

    # Merge with mandatory configuration
    final_config = MANDATORY_CONFIG + "\n" + filtered_config

    # Validate before sending to the backup device
    if not validate_config(final_config):
        print("❌ Synchronization aborted due to incorrect configuration format.")
        return

    # Save configuration to a temporary file
    config_file = "final_config.txt"
    with open(config_file, "w") as file:
        file.write(final_config)

    print("✅ Configuration validated successfully, sending to backup device...")

    # Send file to Backup device via SCP
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(BACKUP["host"], username=BACKUP["username"], password=BACKUP["password"], timeout=10)

        sftp = client.open_sftp()
        sftp.put(config_file, "/var/tmp/final_config.txt")
        sftp.close()

        print("📤 Configuration file successfully sent to Backup device.")

        # Verify file contents on Backup before load override
        print("🔍 Verifying file contents on Backup device...")
        remote_file_content = ssh_command(BACKUP, "cat /var/tmp/final_config.txt")
        print(f"📄 File contents:\n{remote_file_content}")

        # Apply configuration with load override in an interactive session
        print("🛠 Applying configuration with `load override`...")
        ssh_interactive(BACKUP, [
            "configure",
            "load override /var/tmp/final_config.txt",
            "show | compare",
            "commit confirmed 5",
            "commit",
            "exit"
        ])

        print("✅ Synchronization completed successfully!")
        # Execute notification script if synchronization is successful
        subprocess.run(["python3", "notif.py"], check=True)
        client.close()
    except Exception as e:
        print(f"❌ ERROR: Failed to send configuration to Backup: {e}")

def ssh_interactive(device, commands):
    """Execute an interactive SSH session for Juniper."""
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(device["host"], username=device["username"], password=device["password"], timeout=10)
        channel = client.invoke_shell()

        for cmd in commands:
            channel.send(cmd + "\n")
            time.sleep(2)
            while channel.recv_ready():
                output = channel.recv(65535).decode("utf-8")
                print(f"Output [{cmd}]:\n{output}")

        channel.close()
        client.close()
    except Exception as e:
        print(f"❌ ERROR: Failed to run interactive session: {e}")

if __name__ == "__main__":
    sync_config()
