import os
import sqlite3
from datetime import datetime, timezone
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Secrets/configuration are read from environment variables.
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
# Based on the API pattern shown in Zento's BotFather: /api/bot/<TOKEN>/getMe
# If Zento gives you a different base URL, change ZENTO_API_BASE.
ZENTO_API_BASE = os.getenv(
    "ZENTO_API_BASE",
    "https://zento.up.railway.app/api/bot"
).rstrip("/")
ADMIN_ID = os.getenv("ADMIN_ID", "").strip()
DB_PATH = os.getenv("DB_PATH", "bot.db")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            chat_id TEXT NOT NULL,
            name TEXT DEFAULT '',
            username TEXT DEFAULT '',
            points INTEGER DEFAULT 0,
            joined_at TEXT NOT NULL,
            last_seen TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def upsert_user(user_id, chat_id, name="", username=""):
    now = datetime.now(timezone.utc).isoformat()
    conn = db()
    conn.execute("""
        INSERT INTO users(user_id, chat_id, name, username, points, joined_at, last_seen)
        VALUES (?, ?, ?, ?, 0, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            chat_id=excluded.chat_id,
            name=excluded.name,
            username=excluded.username,
            last_seen=excluded.last_seen
    """, (str(user_id), str(chat_id), name, username, now, now))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = db()
    row = conn.execute(
        "SELECT * FROM users WHERE user_id=?",
        (str(user_id),)
    ).fetchone()
    conn.close()
    return row

def count_users():
    conn = db()
    n = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    return n

def add_point(user_id, amount=1):
    conn = db()
    conn.execute(
        "UPDATE users SET points = points + ? WHERE user_id=?",
        (amount, str(user_id))
    )
    conn.commit()
    conn.close()

def send_message(chat_id, text):
    """
    Zento API is configured in one place.
    The endpoint follows the same pattern visible in your screenshot:
    /api/bot/<TOKEN>/METHOD
    """
    url = f"{ZENTO_API_BASE}/{BOT_TOKEN}/sendMessage"
    response = requests.post(
        url,
        json={"chat_id": chat_id, "text": text},
        timeout=15
    )
    response.raise_for_status()
    return response.json()

def extract_message(update):
    """
    Supports the common Bot API-style update shape:
    {"message":{"chat":{"id":...},"from":{...},"text":"..."}}
    """
    message = update.get("message") or update.get("msg") or update
    chat = message.get("chat") or {}
    sender = message.get("from") or message.get("user") or {}

    chat_id = chat.get("id") or message.get("chat_id")
    user_id = sender.get("id") or message.get("user_id") or chat_id
    text = message.get("text") or message.get("message") or ""

    name = (
        sender.get("first_name")
        or sender.get("name")
        or message.get("name")
        or ""
    )
    username = sender.get("username") or ""

    return chat_id, user_id, str(text).strip(), name, username

@app.get("/")
def home():
    return "Zento bot is running."

@app.get("/health")
def health():
    return jsonify({
        "ok": True,
        "users": count_users()
    })

@app.post("/webhook")
def webhook():
    update = request.get_json(silent=True) or {}

    try:
        chat_id, user_id, text, name, username = extract_message(update)

        if chat_id is None:
            # We received a request but it doesn't look like a message.
            return jsonify({"ok": True, "ignored": True})

        upsert_user(user_id, chat_id, name, username)

        if text in ("/start", "start"):
            add_point(user_id, 1)
            send_message(
                chat_id,
                "🤖 سلام! به ربات من خوش اومدی.\n\n"
                "دستورهای موجود:\n"
                "👤 /profile — پروفایل من\n"
                "⭐ /points — امتیاز من\n"
                "📚 /help — راهنما"
            )

        elif text in ("/help", "help"):
            send_message(
                chat_id,
                "📚 راهنما\n\n"
                "/start شروع ربات\n"
                "/profile پروفایل\n"
                "/points امتیاز\n"
                "/help راهنما\n\n"
                "هر پیام معمولی هم برای تست دریافت می‌شود."
            )

        elif text in ("/profile", "profile"):
            user = get_user(user_id)
            send_message(
                chat_id,
                f"👤 پروفایل\n\n"
                f"نام: {user['name'] or 'ثبت نشده'}\n"
                f"شناسه: {user['user_id']}\n"
                f"امتیاز: {user['points']}"
            )

        elif text in ("/points", "points"):
            user = get_user(user_id)
            send_message(
                chat_id,
                f"⭐ امتیاز شما: {user['points']}"
            )

        elif text in ("/stats", "stats"):
            if ADMIN_ID and str(user_id) == ADMIN_ID:
                send_message(
                    chat_id,
                    f"📊 آمار ربات\n\nتعداد کاربران: {count_users()}"
                )
            else:
                send_message(chat_id, "⛔ این دستور فقط برای مدیر است.")

        else:
            # Simple first-version behavior:
            send_message(
                chat_id,
                f"✅ پیام شما دریافت شد.\n\n"
                f"شما گفتید:\n{text}\n\n"
                f"برای راهنما /help را بفرست."
            )

        return jsonify({"ok": True})

    except Exception as exc:
        app.logger.exception("Webhook error")
        # Returning 200 prevents a provider that retries on non-2xx
        # from flooding the bot while we are developing.
        return jsonify({"ok": False, "error": str(exc)}), 200

init_db()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
