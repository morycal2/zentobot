# ZENTO AI Bot — Railway + Bale/Zento

این نسخه، آپلودر قبلی را نگه می‌دارد و بخش ZENTO AI را اضافه می‌کند.

## معماری

- 🎙️ ویس → Groq Whisper → متن
- 💬 متن → OpenRouter → پاسخ AI
- 🖼️ توضیح متن → Hugging Face Inference → تصویر
- همه بخش‌ها با دکمه‌های شیشه‌ای (Inline Keyboard) انتخاب می‌شوند.

## متغیرهای Railway

حداقل این‌ها را تنظیم کن:

`BOT_TOKEN`
`ZENTO_API_BASE`
`ADMIN_ID`
`GROQ_API_KEY`
`OPENROUTER_API_KEY`
`HF_TOKEN`

برای تنظیم مدل‌ها:

`GROQ_STT_MODEL=whisper-large-v3-turbo`
`OPENROUTER_MODEL=openai/gpt-5.4-mini`
`HF_IMAGE_MODEL=black-forest-labs/FLUX.1-schnell`

برای دانلود فایل صوتی:

`BALE_FILE_BASE_URL=https://tapi.bale.ai/file`

اگر پروکسی Zento آدرس فایل را به شکل دیگری برمی‌گرداند، `BALE_FILE_BASE_URL` را مطابق API خودت تغییر بده.

## Railway

1. فایل‌های این ZIP را روی GitHub/Repository خودت قرار بده.
2. Railway را به Repository وصل کن.
3. Environment Variables را وارد کن.
4. Deploy کن.
5. آدرس `/health` را باز کن؛ باید `zento_ai: true` ببینی.
6. Webhook را مطابق روش فعلی Zento/Bale روی `/webhook` نگه دار.

## استفاده در ربات

از `/start` وارد منوی اصلی شو و روی `🤖 ZENTO AI` بزن.

- `🎙️ ویس → متن`: ویس بفرست.
- `💬 متن → AI`: متن بفرست و پاسخ OpenRouter را دریافت کن.
- `🖼️ متن → عکس`: توضیح تصویر را بفرست تا تصویر تولید شود.

## نکته مهم برای عکس

ارسال تصویر تولیدشده از Hugging Face از طریق `sendPhoto` به صورت multipart انجام می‌شود. اگر endpoint پروکسی Zento شما آپلود multipart را قبول نکند، باید endpoint آپلود تصویر پروکسی را با API واقعی Zento هماهنگ کنی.

## APIهای استفاده‌شده

Groq برای transcription از endpoint سازگار با OpenAI استفاده می‌شود.
OpenRouter برای Chat Completions استفاده می‌شود.
Hugging Face Inference برای text-to-image استفاده می‌شود.

کلیدهای API را داخل کد یا GitHub قرار نده؛ فقط در Railway Variables بگذار.
