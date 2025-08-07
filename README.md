# 🎯 ربات مادر - سازنده ربات‌های فروش VPN

یک سیستم کامل و خودکار برای ساخت، مدیریت و نصب ربات‌های فروش VPN با قابلیت‌های پیشرفته.

## 🌟 ویژگی‌ها

### 🤖 ربات مادر
- ساخت خودکار ربات‌های فروش VPN
- پشتیبانی از تنظیمات شخصی (توکن، ادمین، کانال)
- نصب و راه‌اندازی خودکار روی سرور
- مدیریت کامل ربات‌های ساخته شده
- مانیتورینگ و آمارگیری

### 🌐 پنل کنترل وب
- داشبورد مدیریت با رابط کاربری زیبا
- مشاهده آمار و وضعیت ربات‌ها
- کنترل ربات‌ها (شروع، توقف، حذف)
- مشاهده لاگ‌ها و مانیتورینگ سیستم
- مدیریت کاربران

### 🛒 ربات‌های فروش VPN
- سیستم فروش کامل اشتراک VPN
- پنل مدیریت پیشرفته برای ادمین
- پشتیبانی از چندین پنل مرزبان
- سیستم پرداخت و تایید خودکار
- مدیریت کارت‌های بانکی
- سیستم تست رایگان
- قفل عضویت کانال
- کدهای تخفیف
- یادآوری تمدید
- آمارگیری دقیق

## 🚀 نصب و راه‌اندازی

### پیش‌نیازها
- سرور Ubuntu/Debian
- دسترسی root
- اتصال به اینترنت

### نصب خودکار
```bash
# دانلود فایل‌ها
git clone [repository-url]
cd master-bot

# اجرای اسکریپت نصب
sudo chmod +x install.sh
sudo ./install.sh
```

### تنظیمات اولیه
1. توکن ربات مادر را از [@BotFather](https://t.me/BotFather) دریافت کنید
2. آیدی عددی خود را از [@userinfobot](https://t.me/userinfobot) بگیرید
3. فایل تنظیمات را ویرایش کنید:

```bash
sudo nano /opt/master-bot/config.py
```

```python
# Master Bot Configuration
MASTER_BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
ADMIN_ID = YOUR_TELEGRAM_ID
```

4. ربات را راه‌اندازی کنید:
```bash
/opt/master-bot/start.sh
```

## 📋 استفاده

### ربات مادر
1. ربات مادر را در تلگرام استارت کنید
2. روی "🤖 ساخت ربات جدید" کلیک کنید
3. اطلاعات خواسته شده را وارد کنید:
   - توکن ربات جدید
   - آیدی عددی ادمین
   - اطلاعات کانال (اختیاری)
4. ربات به صورت خودکار ساخته و نصب می‌شود

### پنل وب
- آدرس: `http://YOUR_SERVER_IP`
- نام کاربری: `admin`
- رمز عبور: `admin123` (حتماً تغییر دهید!)

## 🔧 مدیریت

### دستورات مفید
```bash
# راه‌اندازی
/opt/master-bot/start.sh

# متوقف کردن
/opt/master-bot/stop.sh

# بروزرسانی
/opt/master-bot/update.sh

# پشتیبان‌گیری
/opt/master-bot/backup.sh

# مانیتورینگ
/opt/master-bot/monitor.sh
```

### مشاهده لاگ‌ها
```bash
# لاگ ربات مادر
journalctl -u master-bot -f

# لاگ پنل وب
journalctl -u master-bot-web -f

# لاگ nginx
journalctl -u nginx -f
```

## 📁 ساختار پروژه

```
master-bot/
├── master_bot.py          # ربات مادر اصلی
├── web_panel.py           # پنل کنترل وب
├── VPNBot                 # قالب ربات VPN
├── install.sh             # اسکریپت نصب
├── templates/             # قالب‌های HTML
├── README.md             # راهنما
└── requirements.txt      # وابستگی‌ها
```

## 🔒 امنیت

### تنظیمات امنیتی
- تغییر رمز عبور پیش‌فرض پنل وب
- استفاده از HTTPS (توصیه می‌شود)
- محدود کردن دسترسی به پنل وب
- پشتیبان‌گیری منظم

### فایروال
```bash
# اجازه دسترسی به پورت‌های ضروری
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 22/tcp
ufw enable
```

## 🛠️ عیب‌یابی

### مشکلات رایج

#### ربات مادر کار نمی‌کند
```bash
# بررسی وضعیت سرویس
systemctl status master-bot

# بررسی لاگ‌ها
journalctl -u master-bot -n 50
```

#### پنل وب در دسترس نیست
```bash
# بررسی nginx
systemctl status nginx

# بررسی پنل وب
systemctl status master-bot-web
```

#### ربات ساخته شده کار نمی‌کند
```bash
# فهرست ربات‌ها
systemctl list-units | grep vpnbot

# بررسی وضعیت ربات خاص
systemctl status vpnbot_BOTNAME.service
```

## 🔄 بروزرسانی

```bash
# بروزرسانی خودکار
/opt/master-bot/update.sh

# بروزرسانی دستی
cd /opt/master-bot
git pull
systemctl restart master-bot
systemctl restart master-bot-web
```

## 💾 پشتیبان‌گیری و بازیابی

### پشتیبان‌گیری
```bash
# پشتیبان‌گیری خودکار
/opt/master-bot/backup.sh

# پشتیبان‌گیری دستی
cp /opt/master-bot/master_bot.db ~/backup/
tar -czf ~/backup/generated_bots.tar.gz /workspace/generated_bots/
```

### بازیابی
```bash
# بازیابی دیتابیس
cp ~/backup/master_bot.db /opt/master-bot/

# بازیابی ربات‌ها
tar -xzf ~/backup/generated_bots.tar.gz -C /
```

## 📊 مانیتورینگ

### آمار سیستم
- CPU، RAM، Disk Usage
- تعداد ربات‌های فعال
- تعداد کاربران
- آمار فروش

### هشدارها
- ربات‌های غیرفعال
- استفاده بالای منابع
- خطاهای سیستم

## 🤝 پشتیبانی

### راه‌های ارتباطی
- تلگرام: [@YourSupport](https://t.me/YourSupport)
- ایمیل: support@example.com
- مستندات: [Wiki](https://github.com/your-repo/wiki)

### سوالات متداول

**Q: چند ربات می‌توانم بسازم؟**
A: محدودیتی وجود ندارد، اما منابع سرور را در نظر بگیرید.

**Q: آیا می‌توانم ربات‌ها را در سرورهای مختلف نصب کنم؟**
A: بله، با تغییرات جزئی در کد امکان‌پذیر است.

**Q: آیا پشتیبانی از پنل‌های دیگر غیر از مرزبان وجود دارد؟**
A: فعلاً فقط مرزبان پشتیبانی می‌شود، اما قابل توسعه است.

## 📝 مجوز

این پروژه تحت مجوز MIT منتشر شده است. برای اطلاعات بیشتر فایل LICENSE را مطالعه کنید.

## 🔮 نقشه راه

### نسخه‌های آتی
- [ ] پشتیبانی از پنل‌های بیشتر
- [ ] رابط کاربری موبایل
- [ ] سیستم پلاگین
- [ ] API عمومی
- [ ] داشبورد تحلیلی پیشرفته

### مشارکت
برای مشارکت در پروژه:
1. Fork کنید
2. یک branch جدید بسازید
3. تغییرات خود را commit کنید
4. Pull Request ایجاد کنید

---

## 📸 تصاویر

### ربات مادر
![Master Bot](screenshots/master-bot.png)

### پنل وب
![Web Panel](screenshots/web-panel.png)

### ربات فروش
![Sales Bot](screenshots/sales-bot.png)

---

**ساخته شده با ❤️ برای جامعه ایرانی**

⭐ اگر این پروژه برایتان مفید بود، حتماً ستاره بدهید!
