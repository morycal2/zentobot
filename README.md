# Zento Bot v1

نسخه اول ربات زنتو با Python، Webhook و SQLite.

## امکانات

- /start
- /help
- /profile
- /points
- /stats برای مدیر
- ذخیره کاربران در SQLite
- ثبت امتیاز
- پاسخ به پیام‌های معمولی
- endpoint سلامت: /health

## راه‌اندازی

1. Python 3.10+ نصب کن.
2. وابستگی‌ها را نصب کن:

```bash
pip install -r requirements.txt
```

3. متغیرهای محیطی را تنظیم کن:

```text
BOT_TOKEN=توکن_ربات
ZENTO_API_BASE=https://zento.up.railway.app/api/bot
ADMIN_ID=شناسه_خودت
```

4. اجرا:

```bash
python app.py
```

برای سرویس‌های ابری، دستور اجرا:

```bash
gunicorn --bind 0.0.0.0:$PORT app:app
```

## اتصال Webhook

بعد از Deploy شدن برنامه، آدرس عمومی HTTPS را در Zento BotFather وارد کن:

```text
https://YOUR-DOMAIN.example/webhook
```

## نکته مهم درباره API زنتو

از تصویر ارسالی شما فقط الگوی زیر را با اطمینان داریم:

```text
/api/bot/<TOKEN>/getMe
```

بنابراین کد `sendMessage` را بر اساس همین الگو نوشته‌ایم:

```text
/api/bot/<TOKEN>/sendMessage
```

اگر Zento در مستندات خودش نام/فرمت دیگری برای ارسال پیام اعلام کند، فقط تابع `send_message` در `app.py` باید اصلاح شود.

## امنیت

توکن را داخل `app.py` ننویس و برای کسی ارسال نکن. آن را فقط به‌عنوان Environment Variable در سرویس میزبانی قرار بده.
