import requests
import time

# Telegram configuration
TELEGRAM_BOT_TOKEN = "qwe1211sdaadwadswadfwf" # Replace with your bot token
TELEGRAM_CHAT_ID = "1234567890"  # Replace with the correct chat ID

def send_telegram_message(message):
    """Send a notification to Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        print("✅ Notification sent to Telegram!")
    else:
        print(f"❌ Failed to send to Telegram: {response.text}")

if __name__ == "__main__":
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    message = (
        "🔔 *Juniper Synchronization Notification*\n"
        "✅ Status: *Successful*\n"
        "🔄 Synchronization between Master and Backup is complete!\n"
        f"📅 Time: {current_time}"
    )
    send_telegram_message(message)
