# Zento Bot v5 — Professional Glass Admin Panel

## پنل مدیریت شیشه‌ای
- `/admin` ورود به داشبورد مدیر اصلی
- داشبورد آمار کاربران، گروه‌ها و اخطارها
- مدیریت فیلتر و بن خودکار با دکمه‌های شیشه‌ای
- روشن/خاموش کردن پاسخ سلام
- مدیریت گروه‌ها و کانال‌های شناخته‌شده
- افزودن/حذف/پاک‌کردن کلمات ممنوع
- ارسال همگانی با `/broadcast متن`
- ارسال به مقصد با `/send CHAT_ID متن`
- بن و آن‌بن با `/ban CHAT_ID USER_ID` و `/unban CHAT_ID USER_ID`
- ریست اخطار با `/resetwarn CHAT_ID USER_ID`

## دسترسی‌ها
`ADMIN_ID` را برابر شناسه کاربری مدیر اصلی قرار بده.

برای حذف پیام و بن، ربات باید در گروه ادمین و دارای دسترسی مربوطه باشد.

## Railway Variables
- BOT_TOKEN
- ZENTO_API_BASE=https://zento.up.railway.app/api/bot
- ADMIN_ID
- DB_PATH=bot.db
- BAD_WORDS=چرت|اسپم|تبلیغ

Webhook: `https://YOUR-RAILWAY-DOMAIN/webhook`
