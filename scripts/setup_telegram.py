"""
Telegram Bot Setup Helper
=========================
Interactive script to set up Telegram notifications for the AI News Pipeline.

Steps:
    1. Message @BotFather on Telegram → /newbot
    2. Copy the bot token
    3. Message your new bot → send any message
    4. Run this script → paste the token
    5. Script fetches your chat ID automatically
    6. Adds both to your .env file
"""

import sys
import httpx
from pathlib import Path
from typing import Optional


def get_bot_info(token: str) -> Optional[dict]:
    """Validate token and get bot info."""
    try:
        resp = httpx.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
        if resp.status_code == 200:
            return resp.json().get("result")
    except Exception:
        pass
    return None


def get_latest_chat_id(token: str) -> Optional[str]:
    """Get the chat_id of the last person who messaged the bot."""
    try:
        resp = httpx.get(f"https://api.telegram.org/bot{token}/getUpdates", timeout=10)
        if resp.status_code == 200:
            updates = resp.json().get("result", [])
            if updates:
                last_update = updates[-1]
                chat = last_update.get("message", {}).get("chat", {})
                return str(chat.get("id", ""))
    except Exception:
        pass
    return None


def send_test_message(token: str, chat_id: str) -> bool:
    """Send a test notification to verify setup."""
    try:
        text = (
            "🤖 <b>AI News Pipeline — Test Notification</b>\n\n"
            "✅ Telegram notifications are working!\n\n"
            "You'll receive messages when:\n"
            "• Pipeline run completes successfully\n"
            "• Pipeline run fails (with error details)\n"
            "• Scheduler starts up\n\n"
            "🎬 Your AI news pipeline is watching 76+ sources across 15+ countries."
        )
        resp = httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
        return resp.status_code == 200
    except Exception:
        return False


def update_env_file(token: str, chat_id: str):
    """Add Telegram credentials to .env file."""
    env_path = Path(".env")
    lines = []
    found_token = False
    found_chat = False

    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("TELEGRAM_BOT_TOKEN="):
                lines.append(f"TELEGRAM_BOT_TOKEN={token}")
                found_token = True
            elif line.startswith("TELEGRAM_CHAT_ID="):
                lines.append(f"TELEGRAM_CHAT_ID={chat_id}")
                found_chat = True
            else:
                lines.append(line)

    if not found_token:
        lines.append(f"TELEGRAM_BOT_TOKEN={token}")
    if not found_chat:
        lines.append(f"TELEGRAM_CHAT_ID={chat_id}")

    env_path.write_text("\n".join(lines) + "\n")
    print(f"✅ Updated {env_path}")


def main():
    print("=" * 55)
    print("  TELEGRAM BOT SETUP — AI News Pipeline")
    print("=" * 55)

    print("\n📋 Setup Instructions:")
    print("  1. Open Telegram and search for @BotFather")
    print("  2. Send /newbot and follow the prompts")
    print("  3. Copy the bot token (looks like: 123456:ABC-DEF...)")
    print("  4. Message your new bot (send 'Hi' or anything)")
    print("  5. Paste the token below\n")

    token = input("🤖 Bot Token: ").strip()
    if not token:
        print("❌ No token provided. Exiting.")
        sys.exit(1)

    # Validate token
    print("\n🔍 Validating token...")
    bot_info = get_bot_info(token)
    if not bot_info:
        print("❌ Invalid token. Make sure you copied the full token from @BotFather.")
        sys.exit(1)

    print(f"✅ Bot found: @{bot_info.get('username', 'unknown')}")

    # Get chat ID
    print("\n🔍 Fetching your chat ID...")
    print("   (Make sure you've sent at least one message to your bot)")

    chat_id = get_latest_chat_id(token)
    if not chat_id:
        print("❌ Could not find your chat ID.")
        print("   Make sure you've sent a message to your bot, then try again.")
        sys.exit(1)

    print(f"✅ Chat ID found: {chat_id}")

    # Send test message
    print("\n📤 Sending test notification...")
    if send_test_message(token, chat_id):
        print("✅ Test notification sent! Check your Telegram.")
    else:
        print("⚠️  Could not send test message, but credentials are valid.")

    # Save to .env
    print("\n💾 Saving to .env file...")
    update_env_file(token, chat_id)

    print("\n" + "=" * 55)
    print("  ✅ SETUP COMPLETE!")
    print("=" * 55)
    print("\n  You'll now receive Telegram notifications for:")
    print("  • ✅ Successful pipeline runs (with article + YouTube link)")
    print("  • ❌ Failed runs (with error details + which step failed)")
    print("  • 🚀 Scheduler startup confirmation")
    print("\n  Test it: python scripts/run_pipeline.py")
    print("=" * 55)


if __name__ == "__main__":
    main()
