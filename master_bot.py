#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Master Bot - ربات مادر برای ساخت و مدیریت ربات‌های فروش VPN
این ربات قابلیت ساخت، نصب و مدیریت ربات‌های فروش VPN را دارد
"""

import os
import sys
import json
import sqlite3
import logging
import asyncio
import subprocess
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import requests
import psutil

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)
from telegram.constants import ParseMode
from telegram.error import TelegramError

# --- Configuration ---
MASTER_BOT_TOKEN = "YOUR_MASTER_BOT_TOKEN_HERE"
ADMIN_ID = 0  # Your Telegram ID
BOTS_DIR = "/workspace/generated_bots"
DB_NAME = "master_bot.db"

# --- Conversation States ---
(
    MAIN_MENU, CREATE_BOT_MENU, 
    AWAIT_BOT_TOKEN, AWAIT_ADMIN_ID, AWAIT_CHANNEL_INFO,
    MANAGE_BOTS_MENU, BOT_DETAILS_MENU,
    EDIT_BOT_MENU, AWAIT_EDIT_VALUE
) = range(9)

# --- Logging ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class MasterBotManager:
    def __init__(self):
        self.db_setup()
        
    def db_setup(self):
        """Setup database for master bot"""
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            
            # Table for generated bots
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS generated_bots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bot_name TEXT NOT NULL,
                    bot_token TEXT NOT NULL UNIQUE,
                    admin_id INTEGER NOT NULL,
                    channel_username TEXT,
                    channel_id INTEGER,
                    status TEXT DEFAULT 'stopped',
                    created_at TEXT NOT NULL,
                    last_started TEXT,
                    process_id INTEGER,
                    port INTEGER UNIQUE,
                    webhook_url TEXT,
                    bot_directory TEXT NOT NULL
                )
            """)
            
            # Table for bot statistics
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bot_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bot_id INTEGER NOT NULL,
                    users_count INTEGER DEFAULT 0,
                    orders_count INTEGER DEFAULT 0,
                    revenue INTEGER DEFAULT 0,
                    last_updated TEXT,
                    FOREIGN KEY (bot_id) REFERENCES generated_bots(id)
                )
            """)
            
            # Table for master bot users
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS master_users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    join_date TEXT,
                    is_premium BOOLEAN DEFAULT 0,
                    bots_created INTEGER DEFAULT 0
                )
            """)
            
            conn.commit()
    
    def get_available_port(self) -> int:
        """Find available port for new bot"""
        used_ports = self.query_db("SELECT port FROM generated_bots WHERE port IS NOT NULL")
        used_ports = [p['port'] for p in used_ports if p['port']]
        
        for port in range(8001, 9000):
            if port not in used_ports and not self.is_port_in_use(port):
                return port
        raise Exception("No available ports found")
    
    def is_port_in_use(self, port: int) -> bool:
        """Check if port is in use"""
        try:
            for conn in psutil.net_connections():
                if conn.laddr.port == port:
                    return True
            return False
        except:
            return False
    
    def query_db(self, query: str, args=(), one=False):
        """Query database"""
        try:
            with sqlite3.connect(DB_NAME) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, args)
                r = cursor.fetchall()
                return (dict(r[0]) if r and r[0] else None) if one else [dict(row) for row in r]
        except sqlite3.Error as e:
            logger.error(f"DB query error: {e}")
            return None if one else []
    
    def execute_db(self, query: str, args=()):
        """Execute database query"""
        try:
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute(query, args)
                conn.commit()
                return cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f"DB execute error: {e}")
            return None

    def generate_bot_code(self, bot_token: str, admin_id: int, channel_username: str = None, channel_id: int = None) -> str:
        """Generate VPN bot code with custom parameters"""
        
        # Read the original VPN bot code
        with open('VPNBot', 'r', encoding='utf-8') as f:
            original_code = f.read()
        
        # Replace configuration values
        modified_code = original_code.replace(
            'BOT_TOKEN = "7910215097:AAH-Zalti5nDFPTS8Dokw0Tgcgb3EpibGEc"',
            f'BOT_TOKEN = "{bot_token}"'
        )
        
        modified_code = modified_code.replace(
            'ADMIN_ID = 6839887159',
            f'ADMIN_ID = {admin_id}'
        )
        
        if channel_username:
            modified_code = modified_code.replace(
                'CHANNEL_USERNAME = "@wings_iran"',
                f'CHANNEL_USERNAME = "{channel_username}"'
            )
        
        if channel_id:
            modified_code = modified_code.replace(
                'CHANNEL_ID = -1001553094061',
                f'CHANNEL_ID = {channel_id}'
            )
        
        return modified_code
    
    def create_bot_directory(self, bot_name: str) -> str:
        """Create directory for new bot"""
        bot_dir = os.path.join(BOTS_DIR, f"bot_{bot_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        os.makedirs(bot_dir, exist_ok=True)
        return bot_dir
    
    def deploy_bot(self, bot_id: int) -> Tuple[bool, str]:
        """Deploy bot to server"""
        try:
            bot_data = self.query_db("SELECT * FROM generated_bots WHERE id = ?", (bot_id,), one=True)
            if not bot_data:
                return False, "Bot not found"
            
            bot_dir = bot_data['bot_directory']
            bot_file = os.path.join(bot_dir, 'vpn_bot.py')
            
            # Generate requirements.txt
            requirements = """python-telegram-bot==20.7
requests==2.31.0
psutil==5.9.6
sqlite3
asyncio
uuid
csv
io
datetime
"""
            
            with open(os.path.join(bot_dir, 'requirements.txt'), 'w') as f:
                f.write(requirements)
            
            # Create systemd service file
            service_content = f"""[Unit]
Description=VPN Sales Bot - {bot_data['bot_name']}
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory={bot_dir}
Environment=PYTHONPATH={bot_dir}
ExecStart=/usr/bin/python3 {bot_file}
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
            
            service_file = f"/etc/systemd/system/vpnbot_{bot_data['bot_name']}.service"
            with open(service_file, 'w') as f:
                f.write(service_content)
            
            # Reload systemd and start service
            subprocess.run(['systemctl', 'daemon-reload'], check=True)
            subprocess.run(['systemctl', 'enable', f"vpnbot_{bot_data['bot_name']}.service"], check=True)
            subprocess.run(['systemctl', 'start', f"vpnbot_{bot_data['bot_name']}.service"], check=True)
            
            # Update status
            self.execute_db(
                "UPDATE generated_bots SET status = 'running', last_started = ? WHERE id = ?",
                (datetime.now().isoformat(), bot_id)
            )
            
            return True, "Bot deployed successfully"
            
        except Exception as e:
            logger.error(f"Error deploying bot {bot_id}: {e}")
            return False, str(e)
    
    def stop_bot(self, bot_id: int) -> Tuple[bool, str]:
        """Stop running bot"""
        try:
            bot_data = self.query_db("SELECT * FROM generated_bots WHERE id = ?", (bot_id,), one=True)
            if not bot_data:
                return False, "Bot not found"
            
            service_name = f"vpnbot_{bot_data['bot_name']}.service"
            subprocess.run(['systemctl', 'stop', service_name], check=True)
            subprocess.run(['systemctl', 'disable', service_name], check=True)
            
            # Update status
            self.execute_db("UPDATE generated_bots SET status = 'stopped' WHERE id = ?", (bot_id,))
            
            return True, "Bot stopped successfully"
            
        except Exception as e:
            logger.error(f"Error stopping bot {bot_id}: {e}")
            return False, str(e)
    
    def delete_bot(self, bot_id: int) -> Tuple[bool, str]:
        """Delete bot completely"""
        try:
            bot_data = self.query_db("SELECT * FROM generated_bots WHERE id = ?", (bot_id,), one=True)
            if not bot_data:
                return False, "Bot not found"
            
            # Stop bot first
            self.stop_bot(bot_id)
            
            # Remove service file
            service_file = f"/etc/systemd/system/vpnbot_{bot_data['bot_name']}.service"
            if os.path.exists(service_file):
                os.remove(service_file)
            
            # Remove bot directory
            if os.path.exists(bot_data['bot_directory']):
                shutil.rmtree(bot_data['bot_directory'])
            
            # Remove from database
            self.execute_db("DELETE FROM generated_bots WHERE id = ?", (bot_id,))
            self.execute_db("DELETE FROM bot_stats WHERE bot_id = ?", (bot_id,))
            
            subprocess.run(['systemctl', 'daemon-reload'], check=True)
            
            return True, "Bot deleted successfully"
            
        except Exception as e:
            logger.error(f"Error deleting bot {bot_id}: {e}")
            return False, str(e)
    
    def get_bot_status(self, bot_id: int) -> Dict:
        """Get detailed bot status"""
        bot_data = self.query_db("SELECT * FROM generated_bots WHERE id = ?", (bot_id,), one=True)
        if not bot_data:
            return {}
        
        try:
            # Check systemd service status
            result = subprocess.run(
                ['systemctl', 'is-active', f"vpnbot_{bot_data['bot_name']}.service"],
                capture_output=True, text=True
            )
            service_status = result.stdout.strip()
            
            # Get bot statistics
            stats = self.query_db("SELECT * FROM bot_stats WHERE bot_id = ?", (bot_id,), one=True)
            
            return {
                'bot_data': bot_data,
                'service_status': service_status,
                'stats': stats or {}
            }
        except Exception as e:
            logger.error(f"Error getting bot status: {e}")
            return {'bot_data': bot_data, 'service_status': 'unknown', 'stats': {}}

# Initialize manager
manager = MasterBotManager()

# --- Helper Functions ---
async def register_master_user(user):
    """Register user in master bot"""
    if not manager.query_db("SELECT 1 FROM master_users WHERE user_id = ?", (user.id,), one=True):
        manager.execute_db(
            "INSERT INTO master_users (user_id, username, first_name, join_date) VALUES (?, ?, ?, ?)",
            (user.id, user.username, user.first_name, datetime.now().isoformat())
        )

# --- Bot Handlers ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start command handler"""
    await register_master_user(update.effective_user)
    
    keyboard = [
        [InlineKeyboardButton("🤖 ساخت ربات جدید", callback_data="create_new_bot")],
        [InlineKeyboardButton("📊 مدیریت ربات‌ها", callback_data="manage_bots")],
        [InlineKeyboardButton("📈 آمار کلی", callback_data="general_stats")],
        [InlineKeyboardButton("ℹ️ راهنما", callback_data="help_guide")]
    ]
    
    text = """🎯 **ربات مادر - سازنده ربات‌های فروش VPN**

سلام! من ربات مادری هستم که می‌توانم برای شما ربات‌های فروش VPN بسازم و مدیریت کنم.

**قابلیت‌های من:**
🤖 ساخت ربات فروش VPN با تنظیمات شخصی شما
🚀 نصب و راه‌اندازی خودکار روی سرور
📊 مانیتورینگ و آمارگیری
⚙️ مدیریت کامل ربات‌ها
🔄 آپدیت و نگهداری

لطفا یکی از گزینه‌های زیر را انتخاب کنید:"""
    
    if update.callback_query:
        await update.callback_query.message.edit_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN
        )
    
    return MAIN_MENU

async def create_new_bot_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start creating new bot"""
    query = update.callback_query
    await query.answer()
    
    context.user_data['new_bot'] = {}
    
    text = """🤖 **ساخت ربات جدید**

برای ساخت ربات جدید، به اطلاعات زیر نیاز دارم:

1️⃣ **توکن ربات** - از @BotFather دریافت کنید
2️⃣ **آیدی عددی ادمین** - آیدی تلگرام شما
3️⃣ **اطلاعات کانال** (اختیاری) - برای قفل عضویت

لطفا **توکن ربات** خود را ارسال کنید:
مثال: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`"""
    
    await query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN)
    return AWAIT_BOT_TOKEN

async def receive_bot_token(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive bot token"""
    token = update.message.text.strip()
    
    # Validate token format
    if not token or ':' not in token or len(token.split(':')) != 2:
        await update.message.reply_text(
            "❌ فرمت توکن نامعتبر است. لطفا توکن صحیح را وارد کنید.\n"
            "مثال: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`",
            parse_mode=ParseMode.MARKDOWN
        )
        return AWAIT_BOT_TOKEN
    
    # Check if token already exists
    if manager.query_db("SELECT 1 FROM generated_bots WHERE bot_token = ?", (token,), one=True):
        await update.message.reply_text("❌ این توکن قبلاً استفاده شده است.")
        return AWAIT_BOT_TOKEN
    
    # Test token validity
    try:
        test_url = f"https://api.telegram.org/bot{token}/getMe"
        response = requests.get(test_url, timeout=10)
        if response.status_code != 200:
            await update.message.reply_text("❌ توکن نامعتبر است. لطفا توکن صحیح وارد کنید.")
            return AWAIT_BOT_TOKEN
        
        bot_info = response.json()['result']
        context.user_data['new_bot']['token'] = token
        context.user_data['new_bot']['bot_username'] = bot_info.get('username', 'Unknown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در بررسی توکن: {str(e)}")
        return AWAIT_BOT_TOKEN
    
    await update.message.reply_text(
        f"✅ توکن تایید شد!\n"
        f"🤖 نام ربات: @{context.user_data['new_bot']['bot_username']}\n\n"
        f"حالا لطفا **آیدی عددی** خود را وارد کنید:\n"
        f"برای دریافت آیدی خود از ربات @userinfobot استفاده کنید."
    )
    return AWAIT_ADMIN_ID

async def receive_admin_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive admin ID"""
    try:
        admin_id = int(update.message.text.strip())
        context.user_data['new_bot']['admin_id'] = admin_id
        
        keyboard = [
            [InlineKeyboardButton("✅ بدون کانال ادامه بده", callback_data="skip_channel")],
            [InlineKeyboardButton("📢 تنظیم کانال", callback_data="set_channel")]
        ]
        
        await update.message.reply_text(
            f"✅ آیدی ادمین ثبت شد: `{admin_id}`\n\n"
            f"آیا می‌خواهید کانال برای قفل عضویت تنظیم کنید؟",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        return AWAIT_CHANNEL_INFO
        
    except ValueError:
        await update.message.reply_text("❌ لطفا فقط عدد وارد کنید.")
        return AWAIT_ADMIN_ID

async def handle_channel_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle channel setup choice"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "skip_channel":
        return await create_bot_final(update, context)
    else:
        await query.message.edit_text(
            "📢 **تنظیم کانال**\n\n"
            "لطفا اطلاعات کانال را به فرمت زیر ارسال کنید:\n"
            "`@channel_username,-1001234567890`\n\n"
            "یا فقط username کانال:\n"
            "`@channel_username`"
        )
        return AWAIT_CHANNEL_INFO

async def receive_channel_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive channel information"""
    channel_info = update.message.text.strip()
    
    if ',' in channel_info:
        parts = channel_info.split(',')
        context.user_data['new_bot']['channel_username'] = parts[0].strip()
        try:
            context.user_data['new_bot']['channel_id'] = int(parts[1].strip())
        except ValueError:
            await update.message.reply_text("❌ فرمت آیدی کانال نامعتبر است.")
            return AWAIT_CHANNEL_INFO
    else:
        context.user_data['new_bot']['channel_username'] = channel_info.strip()
    
    return await create_bot_final(update, context)

async def create_bot_final(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Final step - create the bot"""
    try:
        bot_data = context.user_data['new_bot']
        
        # Show progress message
        if update.callback_query:
            await update.callback_query.message.edit_text("🔄 در حال ساخت ربات... لطفا صبر کنید.")
        else:
            await update.message.reply_text("🔄 در حال ساخت ربات... لطفا صبر کنید.")
        
        # Create bot directory
        bot_name = bot_data['bot_username'].replace('@', '')
        bot_dir = manager.create_bot_directory(bot_name)
        
        # Generate bot code
        generated_code = manager.generate_bot_code(
            bot_data['token'],
            bot_data['admin_id'],
            bot_data.get('channel_username'),
            bot_data.get('channel_id')
        )
        
        # Save bot file
        bot_file = os.path.join(bot_dir, 'vpn_bot.py')
        with open(bot_file, 'w', encoding='utf-8') as f:
            f.write(generated_code)
        
        # Make it executable
        os.chmod(bot_file, 0o755)
        
        # Save to database
        bot_id = manager.execute_db(
            """INSERT INTO generated_bots 
               (bot_name, bot_token, admin_id, channel_username, channel_id, 
                created_at, bot_directory) 
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                bot_name,
                bot_data['token'],
                bot_data['admin_id'],
                bot_data.get('channel_username'),
                bot_data.get('channel_id'),
                datetime.now().isoformat(),
                bot_dir
            )
        )
        
        # Update user stats
        manager.execute_db(
            "UPDATE master_users SET bots_created = bots_created + 1 WHERE user_id = ?",
            (update.effective_user.id,)
        )
        
        # Deploy bot
        success, message = manager.deploy_bot(bot_id)
        
        keyboard = [
            [InlineKeyboardButton("📊 مشاهده جزئیات", callback_data=f"bot_details_{bot_id}")],
            [InlineKeyboardButton("🏠 منوی اصلی", callback_data="main_menu")]
        ]
        
        result_text = f"""✅ **ربات با موفقیت ساخته شد!**

🤖 **نام ربات:** @{bot_name}
👤 **ادمین:** `{bot_data['admin_id']}`
📁 **مسیر:** `{bot_dir}`
🚀 **وضعیت:** {'راه‌اندازی شده' if success else 'خطا در راه‌اندازی'}

{'✅ ربات شما آماده استفاده است!' if success else f'❌ خطا: {message}'}

**نکات مهم:**
• ربات شما به صورت خودکار روی سرور نصب شده
• از منوی مدیریت می‌توانید آن را کنترل کنید
• در صورت بروز مشکل با پشتیبانی تماس بگیرید"""
        
        if update.callback_query:
            await update.callback_query.message.edit_text(
                result_text, 
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(
                result_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
        
        context.user_data.clear()
        return MAIN_MENU
        
    except Exception as e:
        logger.error(f"Error creating bot: {e}")
        error_text = f"❌ خطا در ساخت ربات: {str(e)}"
        
        if update.callback_query:
            await update.callback_query.message.edit_text(error_text)
        else:
            await update.message.reply_text(error_text)
        
        context.user_data.clear()
        return MAIN_MENU

async def manage_bots_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show bots management menu"""
    query = update.callback_query
    await query.answer()
    
    user_bots = manager.query_db(
        "SELECT * FROM generated_bots ORDER BY created_at DESC"
    )
    
    if not user_bots:
        keyboard = [[InlineKeyboardButton("🤖 ساخت اولین ربات", callback_data="create_new_bot")]]
        await query.message.edit_text(
            "📊 **مدیریت ربات‌ها**\n\nشما هنوز هیچ رباتی نساخته‌اید.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return MAIN_MENU
    
    keyboard = []
    text = "📊 **مدیریت ربات‌ها**\n\nلیست ربات‌های شما:\n\n"
    
    for i, bot in enumerate(user_bots, 1):
        status_emoji = "🟢" if bot['status'] == 'running' else "🔴"
        text += f"{i}. {status_emoji} @{bot['bot_name']}\n"
        keyboard.append([
            InlineKeyboardButton(
                f"{status_emoji} @{bot['bot_name']}", 
                callback_data=f"bot_details_{bot['id']}"
            )
        ])
    
    keyboard.extend([
        [InlineKeyboardButton("🤖 ساخت ربات جدید", callback_data="create_new_bot")],
        [InlineKeyboardButton("🔄 بروزرسانی لیست", callback_data="manage_bots")],
        [InlineKeyboardButton("🏠 منوی اصلی", callback_data="main_menu")]
    ])
    
    await query.message.edit_text(
        text, 
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )
    return MANAGE_BOTS_MENU

async def show_bot_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show detailed information about a bot"""
    query = update.callback_query
    await query.answer()
    
    bot_id = int(query.data.split('_')[-1])
    bot_status = manager.get_bot_status(bot_id)
    
    if not bot_status.get('bot_data'):
        await query.message.edit_text("❌ ربات یافت نشد.")
        return MAIN_MENU
    
    bot_data = bot_status['bot_data']
    service_status = bot_status.get('service_status', 'unknown')
    stats = bot_status.get('stats', {})
    
    status_emoji = {
        'active': '🟢',
        'inactive': '🔴',
        'failed': '❌',
        'unknown': '❓'
    }.get(service_status, '❓')
    
    created_date = datetime.fromisoformat(bot_data['created_at']).strftime('%Y/%m/%d %H:%M')
    last_started = 'هرگز' if not bot_data['last_started'] else datetime.fromisoformat(bot_data['last_started']).strftime('%Y/%m/%d %H:%M')
    
    text = f"""📊 **جزئیات ربات @{bot_data['bot_name']}**

🤖 **اطلاعات کلی:**
• وضعیت: {status_emoji} {service_status}
• تاریخ ساخت: {created_date}
• آخرین راه‌اندازی: {last_started}
• ادمین: `{bot_data['admin_id']}`
• کانال: {bot_data['channel_username'] or 'تنظیم نشده'}

📈 **آمار ربات:**
• تعداد کاربران: {stats.get('users_count', 0)}
• تعداد سفارشات: {stats.get('orders_count', 0)}
• درآمد کل: {stats.get('revenue', 0):,} تومان

📁 **مسیر فایل:** `{bot_data['bot_directory']}`"""
    
    keyboard = []
    
    if service_status == 'active':
        keyboard.append([InlineKeyboardButton("⏹️ متوقف کردن", callback_data=f"stop_bot_{bot_id}")])
    else:
        keyboard.append([InlineKeyboardButton("▶️ راه‌اندازی", callback_data=f"start_bot_{bot_id}")])
    
    keyboard.extend([
        [
            InlineKeyboardButton("⚙️ ویرایش", callback_data=f"edit_bot_{bot_id}"),
            InlineKeyboardButton("🔄 بروزرسانی", callback_data=f"bot_details_{bot_id}")
        ],
        [InlineKeyboardButton("🗑️ حذف ربات", callback_data=f"delete_bot_{bot_id}")],
        [InlineKeyboardButton("📊 بازگشت به لیست", callback_data="manage_bots")]
    ])
    
    await query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )
    return BOT_DETAILS_MENU

async def start_bot_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start a bot"""
    query = update.callback_query
    await query.answer()
    
    bot_id = int(query.data.split('_')[-1])
    await query.message.edit_text("🔄 در حال راه‌اندازی ربات...")
    
    success, message = manager.deploy_bot(bot_id)
    
    if success:
        await query.message.edit_text(
            "✅ ربات با موفقیت راه‌اندازی شد!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📊 مشاهده جزئیات", callback_data=f"bot_details_{bot_id}")
            ]])
        )
    else:
        await query.message.edit_text(
            f"❌ خطا در راه‌اندازی ربات:\n{message}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📊 مشاهده جزئیات", callback_data=f"bot_details_{bot_id}")
            ]])
        )
    
    return BOT_DETAILS_MENU

async def stop_bot_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stop a bot"""
    query = update.callback_query
    await query.answer()
    
    bot_id = int(query.data.split('_')[-1])
    await query.message.edit_text("🔄 در حال متوقف کردن ربات...")
    
    success, message = manager.stop_bot(bot_id)
    
    if success:
        await query.message.edit_text(
            "✅ ربات با موفقیت متوقف شد!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📊 مشاهده جزئیات", callback_data=f"bot_details_{bot_id}")
            ]])
        )
    else:
        await query.message.edit_text(
            f"❌ خطا در متوقف کردن ربات:\n{message}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📊 مشاهده جزئیات", callback_data=f"bot_details_{bot_id}")
            ]])
        )
    
    return BOT_DETAILS_MENU

async def delete_bot_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Delete a bot"""
    query = update.callback_query
    await query.answer()
    
    bot_id = int(query.data.split('_')[-1])
    
    keyboard = [
        [InlineKeyboardButton("✅ بله، حذف کن", callback_data=f"confirm_delete_{bot_id}")],
        [InlineKeyboardButton("❌ انصراف", callback_data=f"bot_details_{bot_id}")]
    ]
    
    await query.message.edit_text(
        "⚠️ **هشدار**\n\nآیا مطمئن هستید که می‌خواهید این ربات را حذف کنید؟\n"
        "این عمل غیرقابل بازگشت است و تمام فایل‌ها و تنظیمات ربات حذف خواهد شد.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )
    return BOT_DETAILS_MENU

async def confirm_delete_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirm bot deletion"""
    query = update.callback_query
    await query.answer()
    
    bot_id = int(query.data.split('_')[-1])
    await query.message.edit_text("🔄 در حال حذف ربات...")
    
    success, message = manager.delete_bot(bot_id)
    
    if success:
        await query.message.edit_text(
            "✅ ربات با موفقیت حذف شد!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📊 بازگشت به لیست", callback_data="manage_bots")
            ]])
        )
    else:
        await query.message.edit_text(
            f"❌ خطا در حذف ربات:\n{message}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📊 بازگشت به جزئیات", callback_data=f"bot_details_{bot_id}")
            ]])
        )
    
    return MANAGE_BOTS_MENU

async def show_general_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show general statistics"""
    query = update.callback_query
    await query.answer()
    
    # Get statistics
    total_bots = manager.query_db("SELECT COUNT(*) as count FROM generated_bots", one=True)['count']
    running_bots = manager.query_db("SELECT COUNT(*) as count FROM generated_bots WHERE status = 'running'", one=True)['count']
    total_users = manager.query_db("SELECT COUNT(*) as count FROM master_users", one=True)['count']
    
    # Get top bot creators
    top_creators = manager.query_db("""
        SELECT first_name, bots_created 
        FROM master_users 
        WHERE bots_created > 0 
        ORDER BY bots_created DESC 
        LIMIT 5
    """)
    
    text = f"""📈 **آمار کلی سیستم**

🤖 **ربات‌ها:**
• کل ربات‌های ساخته شده: {total_bots}
• ربات‌های فعال: {running_bots}
• ربات‌های غیرفعال: {total_bots - running_bots}

👥 **کاربران:**
• کل کاربران: {total_users}

🏆 **برترین سازندگان:**"""
    
    for i, creator in enumerate(top_creators, 1):
        text += f"\n{i}. {creator['first_name']}: {creator['bots_created']} ربات"
    
    keyboard = [
        [InlineKeyboardButton("🔄 بروزرسانی", callback_data="general_stats")],
        [InlineKeyboardButton("🏠 منوی اصلی", callback_data="main_menu")]
    ]
    
    await query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )
    return MAIN_MENU

async def show_help_guide(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show help guide"""
    query = update.callback_query
    await query.answer()
    
    text = """📖 **راهنمای استفاده**

**مراحل ساخت ربات:**
1️⃣ از @BotFather یک ربات جدید بسازید
2️⃣ توکن ربات را کپی کنید
3️⃣ از @userinfobot آیدی عددی خود را بگیرید
4️⃣ در ربات مادر روی "ساخت ربات جدید" کلیک کنید
5️⃣ اطلاعات خواسته شده را وارد کنید

**قابلیت‌های ربات ساخته شده:**
🛒 فروش اشتراک VPN
💰 سیستم پرداخت و تایید خودکار
📊 پنل مدیریت کامل
👥 مدیریت کاربران
📈 آمارگیری دقیق
🎁 سیستم تست رایگان
💳 مدیریت کارت‌های بانکی
🔐 قفل عضویت کانال

**پشتیبانی:**
در صورت بروز مشکل با ادمین تماس بگیرید.

**نکات مهم:**
• توکن ربات را با کسی به اشتراک نگذارید
• آیدی عددی خود را دقیق وارد کنید
• ربات‌های ساخته شده به صورت خودکار نصب می‌شوند"""
    
    keyboard = [[InlineKeyboardButton("🏠 منوی اصلی", callback_data="main_menu")]]
    
    await query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )
    return MAIN_MENU

# --- Conversation Handler ---
def main():
    """Main function"""
    # Ensure bots directory exists
    os.makedirs(BOTS_DIR, exist_ok=True)
    
    application = Application.builder().token(MASTER_BOT_TOKEN).build()
    
    # Main conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start_command)],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(create_new_bot_start, pattern='^create_new_bot$'),
                CallbackQueryHandler(manage_bots_menu, pattern='^manage_bots$'),
                CallbackQueryHandler(show_general_stats, pattern='^general_stats$'),
                CallbackQueryHandler(show_help_guide, pattern='^help_guide$'),
                CallbackQueryHandler(start_command, pattern='^main_menu$')
            ],
            AWAIT_BOT_TOKEN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_bot_token)
            ],
            AWAIT_ADMIN_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_admin_id)
            ],
            AWAIT_CHANNEL_INFO: [
                CallbackQueryHandler(handle_channel_choice, pattern='^(skip_channel|set_channel)$'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_channel_info)
            ],
            MANAGE_BOTS_MENU: [
                CallbackQueryHandler(show_bot_details, pattern=r'^bot_details_\d+$'),
                CallbackQueryHandler(create_new_bot_start, pattern='^create_new_bot$'),
                CallbackQueryHandler(manage_bots_menu, pattern='^manage_bots$'),
                CallbackQueryHandler(start_command, pattern='^main_menu$')
            ],
            BOT_DETAILS_MENU: [
                CallbackQueryHandler(start_bot_action, pattern=r'^start_bot_\d+$'),
                CallbackQueryHandler(stop_bot_action, pattern=r'^stop_bot_\d+$'),
                CallbackQueryHandler(delete_bot_action, pattern=r'^delete_bot_\d+$'),
                CallbackQueryHandler(confirm_delete_bot, pattern=r'^confirm_delete_\d+$'),
                CallbackQueryHandler(show_bot_details, pattern=r'^bot_details_\d+$'),
                CallbackQueryHandler(manage_bots_menu, pattern='^manage_bots$')
            ]
        },
        fallbacks=[CommandHandler('start', start_command)]
    )
    
    application.add_handler(conv_handler)
    
    logger.info("Master Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    if MASTER_BOT_TOKEN == "YOUR_MASTER_BOT_TOKEN_HERE" or ADMIN_ID == 0:
        print("❌ لطفا ابتدا MASTER_BOT_TOKEN و ADMIN_ID را در فایل تنظیم کنید!")
        sys.exit(1)
    
    main()