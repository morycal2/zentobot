# Zyro AI 4.0

نسخه حرفه‌ای و سریع Zyro برای Railway.

## قابلیت‌ها
- گفت‌وگوی هوشمند با OpenRouter
- تولید تصویر با Hugging Face Inference Providers و چند مدل fallback
- ساخت TXT / MD / CSV / JSON / PDF / DOCX / XLSX
- ابزارهای خلاصه‌سازی، ترجمه، کدنویسی و گزارش
- منوی حرفه‌ای با متن کامل روی دکمه‌ها
- کار در گروه با Zyro یا @Zyro
- webhook سریع: درخواست بلافاصله 200 می‌گیرد و پردازش AI در worker انجام می‌شود
- SQLite + WAL برای دسترسی سریع‌تر به حافظه

## Railway Variables
همه متغیرهای `.env.example` را تنظیم کن.

برای تصویر، `HF_TOKEN` باید مجوز Inference Providers داشته باشد. `HF_IMAGE_PROVIDER=auto` را نگه دار تا Hugging Face سریع‌ترین Provider در دسترس را انتخاب و در صورت عدم دسترسی failover کند.
