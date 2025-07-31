import sqlite3
from contextlib import contextmanager

DATABASE_NAME = 'ad_bot.db'

@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # جدول المستخدمين
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            balance REAL DEFAULT 0,
            invited_by INTEGER,
            join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # جدول الإعلانات
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS ads (
            ad_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            url TEXT,
            reward REAL DEFAULT 0,
            is_active BOOLEAN DEFAULT 1
        )
        ''')
        
        # جدول المشاهدات
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS ad_views (
            view_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            ad_id INTEGER,
            view_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (ad_id) REFERENCES ads (ad_id)
        )
        ''')
        
        # جدول الدعوات
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS referrals (
            referral_id INTEGER PRIMARY KEY AUTOINCREMENT,
            inviter_id INTEGER NOT NULL,
            invited_id INTEGER NOT NULL UNIQUE,
            join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (inviter_id) REFERENCES users (user_id),
            FOREIGN KEY (invited_id) REFERENCES users (user_id)
        )
        ''')
        
        conn.commit()

def add_user(user_id, username, first_name, last_name, invited_by=None):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, invited_by)
        VALUES (?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name, invited_by))
        conn.commit()

def get_user_balance(user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        return result['balance'] if result else 0

def update_balance(user_id, amount):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
        UPDATE users 
        SET balance = balance + ? 
        WHERE user_id = ?
        ''', (amount, user_id))
        conn.commit()

def add_ad_view(user_id, ad_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO ad_views (user_id, ad_id)
        VALUES (?, ?)
        ''', (user_id, ad_id))
        conn.commit()

def get_active_ads():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM ads WHERE is_active = 1')
        return cursor.fetchall()

def get_user_referrals(user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
        SELECT COUNT(*) as count FROM referrals 
        WHERE inviter_id = ?
        ''', (user_id,))
        result = cursor.fetchone()
        return result['count'] if result else 0

def add_referral(inviter_id, invited_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO referrals (inviter_id, invited_id)
        VALUES (?, ?)
        ''', (inviter_id, invited_id))
        conn.commit()
