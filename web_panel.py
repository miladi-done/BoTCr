#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web Control Panel - پنل کنترل وب برای مدیریت ربات مادر و ربات‌های ساخته شده
"""

import os
import sqlite3
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import subprocess

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this!

DB_NAME = "master_bot.db"
BOTS_DIR = "/workspace/generated_bots"

class WebPanelManager:
    def __init__(self):
        self.init_web_db()
    
    def init_web_db(self):
        """Initialize web panel database tables"""
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            
            # Admin users table for web panel
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS web_admins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    email TEXT,
                    created_at TEXT NOT NULL,
                    last_login TEXT,
                    is_active BOOLEAN DEFAULT 1
                )
            """)
            
            # Create default admin if not exists
            cursor.execute("SELECT COUNT(*) FROM web_admins")
            if cursor.fetchone()[0] == 0:
                default_hash = generate_password_hash('admin123')
                cursor.execute(
                    "INSERT INTO web_admins (username, password_hash, created_at) VALUES (?, ?, ?)",
                    ('admin', default_hash, datetime.now().isoformat())
                )
            
            conn.commit()
    
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
            print(f"DB query error: {e}")
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
            print(f"DB execute error: {e}")
            return None

    def get_bot_logs(self, bot_name: str, lines: int = 100):
        """Get bot logs from systemd"""
        try:
            result = subprocess.run(
                ['journalctl', '-u', f'vpnbot_{bot_name}.service', '-n', str(lines), '--no-pager'],
                capture_output=True, text=True
            )
            return result.stdout
        except Exception as e:
            return f"Error getting logs: {e}"
    
    def get_system_stats(self):
        """Get system statistics"""
        try:
            # CPU usage
            cpu_result = subprocess.run(['top', '-bn1'], capture_output=True, text=True)
            cpu_line = [line for line in cpu_result.stdout.split('\n') if 'Cpu(s)' in line][0]
            cpu_usage = cpu_line.split(',')[0].split(':')[1].strip().split('%')[0]
            
            # Memory usage
            mem_result = subprocess.run(['free', '-m'], capture_output=True, text=True)
            mem_lines = mem_result.stdout.split('\n')[1].split()
            total_mem = int(mem_lines[1])
            used_mem = int(mem_lines[2])
            mem_usage = (used_mem / total_mem) * 100
            
            # Disk usage
            disk_result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True)
            disk_line = disk_result.stdout.split('\n')[1].split()
            disk_usage = disk_line[4].replace('%', '')
            
            return {
                'cpu_usage': float(cpu_usage),
                'memory_usage': round(mem_usage, 1),
                'disk_usage': int(disk_usage),
                'total_memory': total_mem,
                'used_memory': used_mem
            }
        except Exception as e:
            return {
                'cpu_usage': 0,
                'memory_usage': 0,
                'disk_usage': 0,
                'total_memory': 0,
                'used_memory': 0,
                'error': str(e)
            }

web_manager = WebPanelManager()

# --- Authentication ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = web_manager.query_db(
            "SELECT * FROM web_admins WHERE username = ? AND is_active = 1",
            (username,), one=True
        )
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            
            # Update last login
            web_manager.execute_db(
                "UPDATE web_admins SET last_login = ? WHERE id = ?",
                (datetime.now().isoformat(), user['id'])
            )
            
            flash('با موفقیت وارد شدید!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('نام کاربری یا رمز عبور اشتباه است!', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('با موفقیت خارج شدید!', 'info')
    return redirect(url_for('login'))

def login_required(f):
    """Decorator for login required routes"""
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# --- Routes ---
@app.route('/')
@login_required
def dashboard():
    # Get statistics
    total_bots = web_manager.query_db("SELECT COUNT(*) as count FROM generated_bots", one=True)['count']
    running_bots = web_manager.query_db("SELECT COUNT(*) as count FROM generated_bots WHERE status = 'running'", one=True)['count']
    total_users = web_manager.query_db("SELECT COUNT(*) as count FROM master_users", one=True)['count']
    
    # Get recent bots
    recent_bots = web_manager.query_db("""
        SELECT * FROM generated_bots 
        ORDER BY created_at DESC 
        LIMIT 5
    """)
    
    # Get system stats
    system_stats = web_manager.get_system_stats()
    
    return render_template('dashboard.html', 
                         total_bots=total_bots,
                         running_bots=running_bots,
                         total_users=total_users,
                         recent_bots=recent_bots,
                         system_stats=system_stats)

@app.route('/bots')
@login_required
def bots_list():
    bots = web_manager.query_db("SELECT * FROM generated_bots ORDER BY created_at DESC")
    return render_template('bots_list.html', bots=bots)

@app.route('/bot/<int:bot_id>')
@login_required
def bot_details(bot_id):
    bot = web_manager.query_db("SELECT * FROM generated_bots WHERE id = ?", (bot_id,), one=True)
    if not bot:
        flash('ربات یافت نشد!', 'error')
        return redirect(url_for('bots_list'))
    
    # Get bot status
    try:
        result = subprocess.run(
            ['systemctl', 'is-active', f"vpnbot_{bot['bot_name']}.service"],
            capture_output=True, text=True
        )
        service_status = result.stdout.strip()
    except:
        service_status = 'unknown'
    
    # Get bot stats
    stats = web_manager.query_db("SELECT * FROM bot_stats WHERE bot_id = ?", (bot_id,), one=True)
    
    return render_template('bot_details.html', 
                         bot=bot, 
                         service_status=service_status,
                         stats=stats or {})

@app.route('/bot/<int:bot_id>/logs')
@login_required
def bot_logs(bot_id):
    bot = web_manager.query_db("SELECT * FROM generated_bots WHERE id = ?", (bot_id,), one=True)
    if not bot:
        return jsonify({'error': 'Bot not found'}), 404
    
    lines = request.args.get('lines', 100, type=int)
    logs = web_manager.get_bot_logs(bot['bot_name'], lines)
    
    return render_template('bot_logs.html', bot=bot, logs=logs)

@app.route('/api/bot/<int:bot_id>/action', methods=['POST'])
@login_required
def bot_action(bot_id):
    action = request.json.get('action')
    
    bot = web_manager.query_db("SELECT * FROM generated_bots WHERE id = ?", (bot_id,), one=True)
    if not bot:
        return jsonify({'success': False, 'message': 'Bot not found'}), 404
    
    service_name = f"vpnbot_{bot['bot_name']}.service"
    
    try:
        if action == 'start':
            subprocess.run(['systemctl', 'start', service_name], check=True)
            web_manager.execute_db(
                "UPDATE generated_bots SET status = 'running', last_started = ? WHERE id = ?",
                (datetime.now().isoformat(), bot_id)
            )
            message = 'ربات با موفقیت راه‌اندازی شد'
            
        elif action == 'stop':
            subprocess.run(['systemctl', 'stop', service_name], check=True)
            web_manager.execute_db("UPDATE generated_bots SET status = 'stopped' WHERE id = ?", (bot_id,))
            message = 'ربات با موفقیت متوقف شد'
            
        elif action == 'restart':
            subprocess.run(['systemctl', 'restart', service_name], check=True)
            web_manager.execute_db(
                "UPDATE generated_bots SET status = 'running', last_started = ? WHERE id = ?",
                (datetime.now().isoformat(), bot_id)
            )
            message = 'ربات با موفقیت راه‌اندازی مجدد شد'
            
        else:
            return jsonify({'success': False, 'message': 'Invalid action'}), 400
        
        return jsonify({'success': True, 'message': message})
        
    except subprocess.CalledProcessError as e:
        return jsonify({'success': False, 'message': f'خطا: {str(e)}'}), 500

@app.route('/api/bot/<int:bot_id>/delete', methods=['DELETE'])
@login_required
def delete_bot(bot_id):
    bot = web_manager.query_db("SELECT * FROM generated_bots WHERE id = ?", (bot_id,), one=True)
    if not bot:
        return jsonify({'success': False, 'message': 'Bot not found'}), 404
    
    try:
        # Stop service
        service_name = f"vpnbot_{bot['bot_name']}.service"
        subprocess.run(['systemctl', 'stop', service_name], check=False)
        subprocess.run(['systemctl', 'disable', service_name], check=False)
        
        # Remove service file
        service_file = f"/etc/systemd/system/{service_name}"
        if os.path.exists(service_file):
            os.remove(service_file)
        
        # Remove bot directory
        if os.path.exists(bot['bot_directory']):
            import shutil
            shutil.rmtree(bot['bot_directory'])
        
        # Remove from database
        web_manager.execute_db("DELETE FROM generated_bots WHERE id = ?", (bot_id,))
        web_manager.execute_db("DELETE FROM bot_stats WHERE bot_id = ?", (bot_id,))
        
        subprocess.run(['systemctl', 'daemon-reload'], check=True)
        
        return jsonify({'success': True, 'message': 'ربات با موفقیت حذف شد'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'خطا: {str(e)}'}), 500

@app.route('/users')
@login_required
def users_list():
    users = web_manager.query_db("SELECT * FROM master_users ORDER BY join_date DESC")
    return render_template('users_list.html', users=users)

@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html')

@app.route('/api/system/stats')
@login_required
def system_stats_api():
    return jsonify(web_manager.get_system_stats())

# --- Templates ---
templates = {
    'base.html': '''<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}پنل کنترل ربات مادر{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body { font-family: 'Vazir', Arial, sans-serif; }
        .sidebar { min-height: 100vh; background: #2c3e50; }
        .sidebar a { color: #ecf0f1; text-decoration: none; padding: 10px 15px; display: block; }
        .sidebar a:hover { background: #34495e; color: #fff; }
        .main-content { margin-right: 250px; }
        .status-running { color: #28a745; }
        .status-stopped { color: #dc3545; }
        .status-unknown { color: #6c757d; }
    </style>
</head>
<body>
    <div class="d-flex">
        <nav class="sidebar position-fixed">
            <div class="p-3">
                <h4 class="text-white">پنل کنترل</h4>
                <hr class="text-white">
                <a href="{{ url_for('dashboard') }}"><i class="fas fa-home"></i> داشبورد</a>
                <a href="{{ url_for('bots_list') }}"><i class="fas fa-robot"></i> ربات‌ها</a>
                <a href="{{ url_for('users_list') }}"><i class="fas fa-users"></i> کاربران</a>
                <a href="{{ url_for('settings') }}"><i class="fas fa-cog"></i> تنظیمات</a>
                <hr class="text-white">
                <a href="{{ url_for('logout') }}"><i class="fas fa-sign-out-alt"></i> خروج</a>
            </div>
        </nav>
        
        <main class="main-content flex-grow-1">
            <div class="container-fluid p-4">
                {% with messages = get_flashed_messages(with_categories=true) %}
                    {% if messages %}
                        {% for category, message in messages %}
                            <div class="alert alert-{{ 'danger' if category == 'error' else category }} alert-dismissible fade show">
                                {{ message }}
                                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                            </div>
                        {% endfor %}
                    {% endif %}
                {% endwith %}
                
                {% block content %}{% endblock %}
            </div>
        </main>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    {% block scripts %}{% endblock %}
</body>
</html>''',

    'login.html': '''{% extends "base.html" %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-4">
        <div class="card">
            <div class="card-header text-center">
                <h4>ورود به پنل</h4>
            </div>
            <div class="card-body">
                <form method="POST">
                    <div class="mb-3">
                        <label class="form-label">نام کاربری</label>
                        <input type="text" name="username" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">رمز عبور</label>
                        <input type="password" name="password" class="form-control" required>
                    </div>
                    <button type="submit" class="btn btn-primary w-100">ورود</button>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}''',

    'dashboard.html': '''{% extends "base.html" %}

{% block content %}
<h1>داشبورد</h1>

<div class="row mb-4">
    <div class="col-md-3">
        <div class="card text-white bg-primary">
            <div class="card-body">
                <div class="d-flex align-items-center">
                    <i class="fas fa-robot fa-2x me-3"></i>
                    <div>
                        <h5>کل ربات‌ها</h5>
                        <h3>{{ total_bots }}</h3>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <div class="col-md-3">
        <div class="card text-white bg-success">
            <div class="card-body">
                <div class="d-flex align-items-center">
                    <i class="fas fa-play fa-2x me-3"></i>
                    <div>
                        <h5>ربات‌های فعال</h5>
                        <h3>{{ running_bots }}</h3>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <div class="col-md-3">
        <div class="card text-white bg-info">
            <div class="card-body">
                <div class="d-flex align-items-center">
                    <i class="fas fa-users fa-2x me-3"></i>
                    <div>
                        <h5>کاربران</h5>
                        <h3>{{ total_users }}</h3>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <div class="col-md-3">
        <div class="card text-white bg-warning">
            <div class="card-body">
                <div class="d-flex align-items-center">
                    <i class="fas fa-server fa-2x me-3"></i>
                    <div>
                        <h5>CPU</h5>
                        <h3>{{ "%.1f"|format(system_stats.cpu_usage) }}%</h3>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<div class="row">
    <div class="col-md-8">
        <div class="card">
            <div class="card-header">
                <h5>ربات‌های اخیر</h5>
            </div>
            <div class="card-body">
                {% if recent_bots %}
                    <div class="table-responsive">
                        <table class="table">
                            <thead>
                                <tr>
                                    <th>نام ربات</th>
                                    <th>وضعیت</th>
                                    <th>تاریخ ساخت</th>
                                    <th>عملیات</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for bot in recent_bots %}
                                <tr>
                                    <td>@{{ bot.bot_name }}</td>
                                    <td>
                                        <span class="badge bg-{{ 'success' if bot.status == 'running' else 'danger' }}">
                                            {{ 'فعال' if bot.status == 'running' else 'غیرفعال' }}
                                        </span>
                                    </td>
                                    <td>{{ bot.created_at[:19] }}</td>
                                    <td>
                                        <a href="{{ url_for('bot_details', bot_id=bot.id) }}" class="btn btn-sm btn-outline-primary">
                                            مشاهده
                                        </a>
                                    </td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                {% else %}
                    <p class="text-muted">هیچ رباتی یافت نشد.</p>
                {% endif %}
            </div>
        </div>
    </div>
    
    <div class="col-md-4">
        <div class="card">
            <div class="card-header">
                <h5>وضعیت سیستم</h5>
            </div>
            <div class="card-body">
                <div class="mb-3">
                    <div class="d-flex justify-content-between">
                        <span>CPU</span>
                        <span>{{ "%.1f"|format(system_stats.cpu_usage) }}%</span>
                    </div>
                    <div class="progress">
                        <div class="progress-bar" style="width: {{ system_stats.cpu_usage }}%"></div>
                    </div>
                </div>
                
                <div class="mb-3">
                    <div class="d-flex justify-content-between">
                        <span>حافظه</span>
                        <span>{{ "%.1f"|format(system_stats.memory_usage) }}%</span>
                    </div>
                    <div class="progress">
                        <div class="progress-bar bg-info" style="width: {{ system_stats.memory_usage }}%"></div>
                    </div>
                </div>
                
                <div class="mb-3">
                    <div class="d-flex justify-content-between">
                        <span>دیسک</span>
                        <span>{{ system_stats.disk_usage }}%</span>
                    </div>
                    <div class="progress">
                        <div class="progress-bar bg-warning" style="width: {{ system_stats.disk_usage }}%"></div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}''',

    'bots_list.html': '''{% extends "base.html" %}

{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <h1>مدیریت ربات‌ها</h1>
</div>

<div class="card">
    <div class="card-body">
        {% if bots %}
            <div class="table-responsive">
                <table class="table">
                    <thead>
                        <tr>
                            <th>نام ربات</th>
                            <th>ادمین</th>
                            <th>کانال</th>
                            <th>وضعیت</th>
                            <th>تاریخ ساخت</th>
                            <th>عملیات</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for bot in bots %}
                        <tr>
                            <td>@{{ bot.bot_name }}</td>
                            <td>{{ bot.admin_id }}</td>
                            <td>{{ bot.channel_username or '-' }}</td>
                            <td>
                                <span class="badge bg-{{ 'success' if bot.status == 'running' else 'danger' }}">
                                    {{ 'فعال' if bot.status == 'running' else 'غیرفعال' }}
                                </span>
                            </td>
                            <td>{{ bot.created_at[:19] }}</td>
                            <td>
                                <a href="{{ url_for('bot_details', bot_id=bot.id) }}" class="btn btn-sm btn-outline-primary">
                                    مشاهده
                                </a>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        {% else %}
            <p class="text-muted text-center">هیچ رباتی یافت نشد.</p>
        {% endif %}
    </div>
</div>
{% endblock %}''',

    'bot_details.html': '''{% extends "base.html" %}

{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <h1>جزئیات ربات @{{ bot.bot_name }}</h1>
    <div>
        <button id="startBtn" class="btn btn-success btn-sm" onclick="botAction('start')" 
                {{ 'disabled' if service_status == 'active' else '' }}>
            <i class="fas fa-play"></i> شروع
        </button>
        <button id="stopBtn" class="btn btn-warning btn-sm" onclick="botAction('stop')"
                {{ 'disabled' if service_status != 'active' else '' }}>
            <i class="fas fa-stop"></i> توقف
        </button>
        <button id="restartBtn" class="btn btn-info btn-sm" onclick="botAction('restart')">
            <i class="fas fa-redo"></i> راه‌اندازی مجدد
        </button>
        <button class="btn btn-danger btn-sm" onclick="deleteBot()">
            <i class="fas fa-trash"></i> حذف
        </button>
    </div>
</div>

<div class="row">
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h5>اطلاعات کلی</h5>
            </div>
            <div class="card-body">
                <table class="table table-borderless">
                    <tr>
                        <td><strong>نام ربات:</strong></td>
                        <td>@{{ bot.bot_name }}</td>
                    </tr>
                    <tr>
                        <td><strong>وضعیت سرویس:</strong></td>
                        <td>
                            <span class="badge bg-{{ 'success' if service_status == 'active' else 'danger' }}">
                                {{ service_status }}
                            </span>
                        </td>
                    </tr>
                    <tr>
                        <td><strong>ادمین:</strong></td>
                        <td>{{ bot.admin_id }}</td>
                    </tr>
                    <tr>
                        <td><strong>کانال:</strong></td>
                        <td>{{ bot.channel_username or 'تنظیم نشده' }}</td>
                    </tr>
                    <tr>
                        <td><strong>تاریخ ساخت:</strong></td>
                        <td>{{ bot.created_at[:19] }}</td>
                    </tr>
                    <tr>
                        <td><strong>آخرین راه‌اندازی:</strong></td>
                        <td>{{ bot.last_started[:19] if bot.last_started else 'هرگز' }}</td>
                    </tr>
                </table>
            </div>
        </div>
    </div>
    
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h5>آمار ربات</h5>
            </div>
            <div class="card-body">
                <table class="table table-borderless">
                    <tr>
                        <td><strong>تعداد کاربران:</strong></td>
                        <td>{{ stats.users_count or 0 }}</td>
                    </tr>
                    <tr>
                        <td><strong>تعداد سفارشات:</strong></td>
                        <td>{{ stats.orders_count or 0 }}</td>
                    </tr>
                    <tr>
                        <td><strong>درآمد کل:</strong></td>
                        <td>{{ "{:,}".format(stats.revenue or 0) }} تومان</td>
                    </tr>
                    <tr>
                        <td><strong>آخرین بروزرسانی:</strong></td>
                        <td>{{ stats.last_updated[:19] if stats.last_updated else 'هرگز' }}</td>
                    </tr>
                </table>
            </div>
        </div>
    </div>
</div>

<div class="row mt-4">
    <div class="col-12">
        <div class="card">
            <div class="card-header d-flex justify-content-between">
                <h5>لاگ‌های ربات</h5>
                <a href="{{ url_for('bot_logs', bot_id=bot.id) }}" class="btn btn-sm btn-outline-primary">
                    مشاهده کامل
                </a>
            </div>
            <div class="card-body">
                <div id="logs" style="height: 300px; overflow-y: scroll; background: #f8f9fa; padding: 15px; font-family: monospace;">
                    در حال بارگذاری...
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
function botAction(action) {
    fetch(`/api/bot/{{ bot.id }}/action`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({action: action})
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert(data.message);
            location.reload();
        } else {
            alert('خطا: ' + data.message);
        }
    });
}

function deleteBot() {
    if (confirm('آیا مطمئن هستید که می‌خواهید این ربات را حذف کنید؟')) {
        fetch(`/api/bot/{{ bot.id }}/delete`, {method: 'DELETE'})
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert(data.message);
                window.location.href = '/bots';
            } else {
                alert('خطا: ' + data.message);
            }
        });
    }
}

// Load logs
fetch(`/bot/{{ bot.id }}/logs`)
    .then(response => response.text())
    .then(html => {
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        const logsContent = doc.querySelector('#logs-content');
        if (logsContent) {
            document.getElementById('logs').innerHTML = logsContent.innerHTML;
        }
    });
</script>
{% endblock %}''',

    'bot_logs.html': '''{% extends "base.html" %}

{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <h1>لاگ‌های ربات @{{ bot.bot_name }}</h1>
    <a href="{{ url_for('bot_details', bot_id=bot.id) }}" class="btn btn-secondary">بازگشت</a>
</div>

<div class="card">
    <div class="card-body">
        <div id="logs-content" style="height: 600px; overflow-y: scroll; background: #000; color: #fff; padding: 15px; font-family: monospace; font-size: 12px;">
            <pre>{{ logs }}</pre>
        </div>
    </div>
</div>
{% endblock %}''',

    'users_list.html': '''{% extends "base.html" %}

{% block content %}
<h1>مدیریت کاربران</h1>

<div class="card">
    <div class="card-body">
        {% if users %}
            <div class="table-responsive">
                <table class="table">
                    <thead>
                        <tr>
                            <th>آیدی</th>
                            <th>نام</th>
                            <th>نام کاربری</th>
                            <th>تعداد ربات‌ها</th>
                            <th>تاریخ عضویت</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for user in users %}
                        <tr>
                            <td>{{ user.user_id }}</td>
                            <td>{{ user.first_name or '-' }}</td>
                            <td>@{{ user.username or '-' }}</td>
                            <td>{{ user.bots_created }}</td>
                            <td>{{ user.join_date[:19] if user.join_date else '-' }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        {% else %}
            <p class="text-muted text-center">هیچ کاربری یافت نشد.</p>
        {% endif %}
    </div>
</div>
{% endblock %}''',

    'settings.html': '''{% extends "base.html" %}

{% block content %}
<h1>تنظیمات</h1>

<div class="row">
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h5>تنظیمات عمومی</h5>
            </div>
            <div class="card-body">
                <p>تنظیمات در نسخه‌های بعدی اضافه خواهد شد.</p>
            </div>
        </div>
    </div>
</div>
{% endblock %}'''
}

# Create templates directory and files
templates_dir = 'templates'
os.makedirs(templates_dir, exist_ok=True)

for filename, content in templates.items():
    with open(os.path.join(templates_dir, filename), 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)