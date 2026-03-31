# Juniper Sync

> ⚠️ **This project is currently under active development and intended for testing purposes only.**

Automatically synchronize configuration from a **Master** Juniper device to a **Backup** Juniper device. The script fetches the running configuration from the Master, filters out specific sections (such as hostname and management interface), merges it with a mandatory base configuration for the Backup device, and applies it using `load override`. A Telegram notification is sent upon successful synchronization.

## How It Works

```
┌────────────┐       SSH        ┌─────────────┐
│   Master   │ ──────────────── │  This Script │
│ (Juniper)  │  Fetch config    │  (Python)    │
└────────────┘                  └──────┬───────┘
                                       │
                          Filter config │ (remove hostname,
                          ge-0/0/0)     │ merge mandatory config
                                       │
                                       ▼
                                ┌─────────────┐       Telegram
                                │   Backup    │ ──────────────── 📩 Notification
                                │  (Juniper)  │  load override
                                └─────────────┘
```

### Synchronization Flow

1. **Fetch** — Retrieve running configuration from the Master device via SSH.
2. **Filter** — Remove `host-name` and `ge-0/0/0` interface block from the fetched configuration.
3. **Merge** — Combine the filtered configuration with a mandatory base configuration (hostname, management interface, static route, etc.) specific to the Backup device.
4. **Validate** — Check that the final configuration has properly matched braces before applying.
5. **Transfer** — Upload the final configuration file to the Backup device via SFTP.
6. **Apply** — Execute `load override` and `commit confirmed` on the Backup device through an interactive SSH session.
7. **Notify** — Send a Telegram notification upon successful synchronization.

## Project Structure

```
juniper-sync/
├── sync-juniper.py     # Main synchronization script
├── notif.py            # Telegram notification module
└── requirements.txt    # Python dependencies
```

## Prerequisites

- **Python** 3.8 or higher
- **Network access** to both Master and Backup Juniper devices via SSH (port 22)
- **Telegram Bot Token** and **Chat ID** for notifications
- Both Juniper devices must have SSH enabled

## Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/your-username/juniper-sync.git
   cd juniper-sync
   ```

2. **Create a virtual environment** (optional)

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

## Configuration

Before running the script, update the following variables directly in the source files:

### `sync-juniper.py`

| Variable | Description |
|---|---|
| `MASTER["host"]` | IP address of the Master Juniper device |
| `MASTER["username"]` | SSH username for the Master device |
| `MASTER["password"]` | SSH password for the Master device |
| `BACKUP["host"]` | IP address of the Backup Juniper device |
| `BACKUP["username"]` | SSH username for the Backup device |
| `BACKUP["password"]` | SSH password for the Backup device |
| `MANDATORY_CONFIG` | Base configuration to always apply on the Backup device (hostname, management interface, static route, syslog, etc.) |

### `notif.py`

| Variable | Description |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Your Telegram Bot API token |
| `TELEGRAM_CHAT_ID` | Target Telegram chat ID for notifications |

## Usage

Run the synchronization script:

```bash
python3 sync-juniper.py
```

### Expected Output

```
📥 Fetching configuration from Master...
✅ Configuration validated successfully, sending to backup device...
📤 Configuration file successfully sent to Backup device.
🔍 Verifying file contents on Backup device...
🛠 Applying configuration with `load override`...
✅ Synchronization completed successfully!
✅ Notification sent to Telegram!
```

## Filtered Configuration

The script automatically **removes** the following sections from the Master configuration before applying to the Backup device:

| Section | Reason |
|---|---|
| `host-name` | The Backup device must retain its own hostname |
| `ge-0/0/0` interface block | Management interface must remain unique per device |

These are then replaced by the `MANDATORY_CONFIG` block defined in the script.

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| `paramiko` | 3.5.0 | SSH and SFTP connectivity to Juniper devices |
| `requests` | 2.33.1 | Sending Telegram API notifications |

## ⚠️ Known Limitations

- Credentials are currently **hardcoded** in the script (environment variables or a secrets manager are planned for future versions).
- The `MANDATORY_CONFIG` block is **static** and must be manually updated if the Backup device configuration changes.
- No **rollback mechanism** beyond Juniper's built-in `commit confirmed` timeout (5 minutes).
- No **logging to file** — all output is printed to stdout.

## License

This project is licensed under the [MIT License](LICENSE).
