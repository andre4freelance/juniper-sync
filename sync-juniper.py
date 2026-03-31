import paramiko
import time
import subprocess

# Konfigurasi perangkat Juniper
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

# Konfigurasi yang wajib ada
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
    """Eksekusi perintah SSH dan kembalikan output."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(device["host"], username=device["username"], password=device["password"], timeout=10)
        stdin, stdout, stderr = client.exec_command(command)
        output = stdout.read().decode("utf-8")
        client.close()
        return output
    except Exception as e:
        print(f"❌ ERROR: Gagal terhubung ke {device['host']}: {e}")
        return None

def filter_config(config):
    """Hapus hostname dan interface ge-0/0/0 dari konfigurasi Master."""
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
    """Validasi format konfigurasi sebelum dikirim ke perangkat."""
    open_braces = config.count("{")
    close_braces = config.count("}")
    
    if open_braces != close_braces:
        print(f"❌ ERROR: Konfigurasi tidak ditutup dengan benar! {open_braces} '{'{'}' vs {close_braces} '{'}'}'")
        return False
    
    return True

def sync_config():
    """Sinkronisasi konfigurasi Master ke Backup menggunakan `load override`."""
    print("📥 Mengambil konfigurasi dari Master...")
    master_config = ssh_command(MASTER, "show configuration | no-more")

    if not master_config:
        print("❌ Gagal mengambil konfigurasi dari Master.")
        return

    # Filter interface ge-0/0/0 dan hostname
    filtered_config = filter_config(master_config)

    # Gabungkan dengan konfigurasi wajib
    final_config = MANDATORY_CONFIG + "\n" + filtered_config

    # Validasi sebelum mengirim ke perangkat backup
    if not validate_config(final_config):
        print("❌ Sinkronisasi dibatalkan karena format konfigurasi salah.")
        return

    # Simpan konfigurasi ke file sementara
    config_file = "final_config.txt"
    with open(config_file, "w") as file:
        file.write(final_config)

    print("✅ Konfigurasi berhasil divalidasi, mengirim ke perangkat backup...")

    # Kirim file ke perangkat Backup via SCP
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(BACKUP["host"], username=BACKUP["username"], password=BACKUP["password"], timeout=10)

        sftp = client.open_sftp()
        sftp.put(config_file, "/var/tmp/final_config.txt")
        sftp.close()

        print("📤 File konfigurasi berhasil dikirim ke perangkat Backup.")

        # Verifikasi isi file di Backup sebelum load override
        print("🔍 Verifikasi isi file di perangkat Backup...")
        remote_file_content = ssh_command(BACKUP, "cat /var/tmp/final_config.txt")
        print(f"📄 Isi file:\n{remote_file_content}")

        # Terapkan konfigurasi dengan load override dalam sesi interaktif
        print("🛠 Menerapkan konfigurasi dengan `load override`...")
        ssh_interactive(BACKUP, [
            "configure",
            "load override /var/tmp/final_config.txt",
            "show | compare",
            "commit confirmed 5",
            "commit",
            "exit"
        ])

        print("✅ Sinkronisasi berhasil dilakukan!")
        # Eksekusi script notifikasi jika sinkronisasi berhasil
        subprocess.run(["python3", "notif.py"], check=True)
        client.close()
    except Exception as e:
        print(f"❌ ERROR: Gagal mengirim konfigurasi ke Backup: {e}")

def ssh_interactive(device, commands):
    """Eksekusi sesi SSH interaktif untuk Juniper."""
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
        print(f"❌ ERROR: Gagal menjalankan sesi interaktif: {e}")

if __name__ == "__main__":
    sync_config()
