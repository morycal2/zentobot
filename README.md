# Zyro Professional

نسخه سریع‌تر و حرفه‌ای‌تر Zyro برای Railway.

## امکانات
- گفت‌وگوی هوش مصنوعی با OpenRouter
- تولید تصویر با Hugging Face Inference Providers و چند مدل جایگزین
- ساخت و ارسال فایل TXT / Markdown / CSV
- حالت‌های پایدار چت، تصویر و فایل
- منوی حرفه‌ای و دکمه‌های شیشه‌ای/inline در API تلگرام
- پاسخ در گروه و کانال با `Zyro` یا `@Zyro`
- حافظه کوتاه گفتگو و `/clear`
- Session mode در SQLite

## متغیرهای Railway
همه متغیرهای `.env.example` را تنظیم کن.

### تصویر
`HF_TOKEN` باید توکن Hugging Face با دسترسی Inference داشته باشد.
`HF_IMAGE_PROVIDER=auto` را نگه دار تا Hugging Face بتواند provider مناسب را انتخاب و در صورت نیاز failover کند.
`HF_IMAGE_MODELS` به‌صورت پیش‌فرض سه مدل را امتحان می‌کند.

اگر تصویر هنوز خطا داد، endpoint `/health` را باز کن تا مدل و provider تنظیم‌شده را ببینی.

## اجرای Railway
Procfile:
`web: gunicorn -w 1 -b 0.0.0.0:$PORT app:app`

## فایل
از منوی «📎 ساخت فایل» استفاده کن. اگر در متن به CSV/Excel اشاره شود فایل CSV ساخته می‌شود؛ برای Markdown فایل MD و در حالت عادی TXT ساخته می‌شود.
