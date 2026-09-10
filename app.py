import os, sqlite3
from datetime import datetime, timezone
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ZENTO_API_BASE = os.getenv(
    "ZENTO_API_BASE",
    "https://zento.up.railway.app/api/bot"
).rstrip("/")
ADMIN_ID = os.getenv("ADMIN_ID", "").strip()
DB_PATH = os.getenv("DB_PATH", "bot.db")


# -------------------------
# Database
# -------------------------
def db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    c = db()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users(
            user_id TEXT PRIMARY KEY,
            username TEXT DEFAULT '',
            first_name TEXT DEFAULT '',
            points INTEGER DEFAULT 0,
            last_daily TEXT DEFAULT ''
        )
    """)
    c.commit()
    c.close()


def upsert_user(uid, username="", first_name=""):
    c = db()
    c.execute("""
        INSERT INTO users(user_id, username, first_name)
        VALUES(?,?,?)
        ON CONFLICT(user_id) DO UPDATE SET
            username=excluded.username,
            first_name=excluded.first_name
    """, (str(uid), username or "", first_name or ""))
    c.commit()
    c.close()


def get_user(uid):
    c = db()
    r = c.execute(
        "SELECT * FROM users WHERE user_id=?",
        (str(uid),)
    ).fetchone()
    c.close()
    return r


def add_points(uid, n):
    c = db()
    c.execute(
        "UPDATE users SET points=points+? WHERE user_id=?",
        (n, str(uid))
    )
    c.commit()
    c.close()


def today():
    return datetime.now(timezone.utc).date().isoformat()


# -------------------------
# Professional glass menu
# -------------------------
def main_menu():
    return {
        "inline_keyboard": [
            [
                {"text": "👤 پروفایل من", "callback_data": "profile"},
                {"text": "⭐ امتیازات", "callback_data": "points"}
            ],
            [
                {"text": "🎁 جایزه روزانه", "callback_data": "daily"},
                {"text": "💬 پشتیبانی", "callback_data": "support"}
            ],
            [
                {"text": "📚 راهنما", "callback_data": "help"},
                {"text": "ℹ️ درباره ربات", "callback_data": "about"}
            ],
            [
                {"text": "🔄 بروزرسانی منو", "callback_data": "menu"}
            ]
        ]
    }


def back_menu():
    return {
        "inline_keyboard": [
            [{"text": "🏠 بازگشت به منوی اصلی", "callback_data": "menu"}]
        ]
    }


def profile_menu():
    return {
        "inline_keyboard": [
            [
                {"text": "⭐ امتیازات من", "callback_data": "points"},
                {"text": "🎁 جایزه روزانه", "callback_data": "daily"}
            ],
            [{"text": "🏠 منوی اصلی", "callback_data": "menu"}]
        ]
    }


def send_message(chat_id, text, reply_markup=None):
    if not BOT_TOKEN:
        return False

    payload = {
        "chat_id": chat_id,
        "text": text
    }

    if reply_markup is not None:
        payload["reply_markup"] = reply_markup

    try:
        r = requests.post(
            f"{ZENTO_API_BASE}/{BOT_TOKEN}/sendMessage",
            json=payload,
            timeout=15
        )
        return r.ok
    except requests.RequestException:
        return False


def edit_message(chat_id, message_id, text, reply_markup=None):
    """Edit an existing inline-keyboard message when the Zento API supports it."""
    if not BOT_TOKEN or not message_id:
        return False

    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text
    }

    if reply_markup is not None:
        payload["reply_markup"] = reply_markup

    try:
        r = requests.post(
            f"{ZENTO_API_BASE}/{BOT_TOKEN}/editMessageText",
            json=payload,
            timeout=15
        )
        return r.ok
    except requests.RequestException:
        return False


def answer_callback(callback_id):
    """Optional Telegram/Bale-compatible callback acknowledgement."""
    if not BOT_TOKEN or not callback_id:
        return False

    try:
        r = requests.post(
            f"{ZENTO_API_BASE}/{BOT_TOKEN}/answerCallbackQuery",
            json={"callback_query_id": callback_id},
            timeout=10
        )
        return r.ok
    except requests.RequestException:
        return False


# -------------------------
# Update parsing
# -------------------------
def parse_message(data):
    m = data.get("message") or data.get("msg")
    if not isinstance(m, dict):
        return (None,) * 5

    ch = m.get("chat") or {}
    s = m.get("from") or m.get("sender") or {}
    text = m.get("text") or ""

    return (
        ch.get("id"),
        s.get("id") or ch.get("id"),
        s.get("username", ""),
        s.get("first_name") or s.get("name") or "",
        text.strip()
    )


def parse_callback(data):
    q = data.get("callback_query") or data.get("callback")
    if not isinstance(q, dict):
        return (None,) * 6

    message = q.get("message") or q.get("msg") or {}
    chat = message.get("chat") or {}
    sender = q.get("from") or q.get("sender") or {}
    data_value = q.get("data") or q.get("callback_data") or ""

    return (
        chat.get("id"),
        sender.get("id") or chat.get("id"),
        sender.get("username", ""),
        sender.get("first_name") or sender.get("name") or "",
        str(data_value).strip(),
        q.get("id") or q.get("callback_query_id")
    )


# -------------------------
# Screens
# -------------------------
def show_home(cid, uid):
    name = get_user(uid)["first_name"] or "دوست من"
    text = (
        f"✨ سلام {name}!\n\n"
        "به ربات زنتو خوش اومدی 🌟\n\n"
        "از منوی زیر می‌تونی امکانات ربات رو مدیریت کنی.\n"
        "برای انتخاب هر بخش، روی دکمه موردنظر بزن 👇"
    )
    send_message(cid, text, main_menu())


def show_profile(cid, uid):
    u = get_user(uid)
    username = f"@{u['username']}" if u["username"] else "ندارد"

    text = (
        "👤 پروفایل کاربری\n\n"
        f"🪪 نام: {u['first_name'] or 'بدون نام'}\n"
        f"🆔 شناسه: {u['user_id']}\n"
        f"🔗 نام کاربری: {username}\n"
        f"⭐ امتیاز: {u['points']}\n\n"
        "حساب کاربری شما با موفقیت ثبت شده است."
    )
    send_message(cid, text, profile_menu())


def show_points(cid, uid):
    points = get_user(uid)["points"]
    text = (
        "⭐ امتیازات شما\n\n"
        f"موجودی امتیاز: {points} ⭐\n\n"
        "با انجام فعالیت‌های ربات می‌تونی امتیاز بیشتری دریافت کنی."
    )
    send_message(cid, text, back_menu())


def show_daily(cid, uid):
    u = get_user(uid)

    if u["last_daily"] == today():
        text = (
            "⏳ جایزه روزانه\n\n"
            "امروز جایزه‌ات رو دریافت کردی.\n"
            "فردا دوباره برگرد 🎁"
        )
    else:
        c = db()
        c.execute(
            "UPDATE users SET points=points+5,last_daily=? WHERE user_id=?",
            (today(), str(uid))
        )
        c.commit()
        c.close()

        text = (
            "🎉 جایزه روزانه دریافت شد!\n\n"
            "+5 ⭐ امتیاز به حساب شما اضافه شد.\n"
            "فردا دوباره برای دریافت جایزه برگرد."
        )

    send_message(cid, text, back_menu())


def show_help(cid):
    text = (
        "📚 راهنمای ربات\n\n"
        "👤 پروفایل — مشاهده اطلاعات حساب\n"
        "⭐ امتیازات — مشاهده امتیازها\n"
        "🎁 جایزه روزانه — دریافت روزانه ۵ امتیاز\n"
        "💬 پشتیبانی — ارتباط با پشتیبانی\n"
        "ℹ️ درباره ربات — اطلاعات نسخه\n\n"
        "برای برگشت، دکمه زیر را بزن 👇"
    )
    send_message(cid, text, back_menu())


def show_support(cid):
    text = (
        "💬 پشتیبانی\n\n"
        "پیامت رو همین‌جا ارسال کن.\n"
        "در نسخه‌های بعدی می‌تونیم سیستم تیکت، صف پشتیبانی "
        "و پنل مدیریت حرفه‌ای هم اضافه کنیم."
    )
    send_message(cid, text, back_menu())


def show_about(cid):
    text = (
        "ℹ️ درباره Zento Bot\n\n"
        "🚀 نسخه: 3.0\n"
        "⚡ Flask + SQLite\n"
        "🎛️ منوی شیشه‌ای حرفه‌ای\n"
        "🔘 دکمه‌های چندمرحله‌ای\n\n"
        "ساخته شده برای یک تجربه سریع و ساده."
    )
    send_message(cid, text, back_menu())


# -------------------------
# Handlers
# -------------------------
def handle_action(cid, uid, username, first_name, action, callback_id=None):
    if cid is None or uid is None:
        return

    upsert_user(uid, username, first_name)

    if callback_id:
        answer_callback(callback_id)

    if action == "menu":
        show_home(cid, uid)

    elif action == "profile":
        show_profile(cid, uid)

    elif action == "points":
        show_points(cid, uid)

    elif action == "daily":
        show_daily(cid, uid)

    elif action == "help":
        show_help(cid)

    elif action == "support":
        show_support(cid)

    elif action == "about":
        show_about(cid, uid)


def handle_message(cid, uid, username, first_name, text):
    if cid is None or uid is None:
        return

    upsert_user(uid, username, first_name)
    cmd = text.lower().strip()

    if cmd in ("/start", "start", "منو", "menu"):
        add_points(uid, 1)
        show_home(cid, uid)

    elif cmd in ("/profile", "👤 پروفایل من", "پروفایل", "profile"):
        show_profile(cid, uid)

    elif cmd in ("/points", "⭐ امتیازات", "امتیازات", "points"):
        show_points(cid, uid)

    elif cmd in ("/daily", "🎁 جایزه روزانه", "جایزه روزانه", "daily"):
        show_daily(cid, uid)

    elif cmd in ("/help", "📚 راهنما", "راهنما", "help"):
        show_help(cid)

    elif cmd in ("/support", "💬 پشتیبانی", "پشتیبانی", "support"):
        show_support(cid)

    elif cmd in ("/about", "ℹ️ درباره ربات", "درباره", "about"):
        show_about(cid)

    elif cmd in ("/stats", "stats", "آمار"):
        if ADMIN_ID and str(uid) != ADMIN_ID:
            send_message(
                cid,
                "⛔ این دستور فقط برای مدیر ربات است.",
                back_menu()
            )
            return

        c = db()
        count = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        total = c.execute(
            "SELECT COALESCE(SUM(points),0) FROM users"
        ).fetchone()[0]
        c.close()

        send_message(
            cid,
            f"📊 آمار ربات\n\n"
            f"👥 کاربران: {count}\n"
            f"⭐ مجموع امتیازها: {total}\n"
            f"🚀 نسخه: 3",
            back_menu()
        )

    else:
        send_message(
            cid,
            "❓ این دستور رو متوجه نشدم.\n\n"
            "برای باز کردن منوی حرفه‌ای /start رو بفرست.",
            main_menu()
        )


# -------------------------
# Routes
# -------------------------
@app.get("/")
def home():
    return "Zento Bot v3 - Professional Glass Menu is running."


@app.get("/health")
def health():
    c = db()
    n = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    c.close()
    return jsonify({
        "ok": True,
        "version": 3,
        "users": n,
        "keyboard": "inline"
    })


@app.post("/webhook")
def webhook():
    data = request.get_json(silent=True) or {}

    # Normal messages
    cid, uid, un, fn, text = parse_message(data)
    if cid is not None:
        handle_message(cid, uid, un, fn, text)

    # Inline button callbacks
    cid, uid, un, fn, action, callback_id = parse_callback(data)
    if cid is not None and action:
        handle_action(cid, uid, un, fn, action, callback_id)

    return jsonify({"ok": True})


init_db()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8080"))
    )
