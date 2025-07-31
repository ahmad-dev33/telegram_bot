import logging
from telegram import __version__ as TG_VER
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters
)

from config import Config
import database as db

# إعداد التسجيل
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """إرسال رسالة الترحيب عند استخدام الأمر /start"""
    user = update.effective_user
    referral_link = f"https://t.me/{context.bot.username}?start=ref_{user.id}"
    
    # تسجيل المستخدم في قاعدة البيانات
    args = context.args
    invited_by = None
    
    if args and args[0].startswith('ref_'):
        try:
            invited_by = int(args[0][4:])
            db.add_referral(invited_by, user.id)
            # مكافأة المدعو
            db.update_balance(invited_by, 5)  # 5 وحدات لكل دعوة
        except (ValueError, IndexError):
            pass
    
    db.add_user(user.id, user.username, user.first_name, user.last_name, invited_by)
    
    keyboard = [
        [InlineKeyboardButton("💰 رصيدي", callback_data="balance")],
        [InlineKeyboardButton("📢 مشاهدة الإعلانات", callback_data="view_ads")],
        [InlineKeyboardButton("👥 دعوة الأصدقاء", callback_data="invite_friends")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_message = f"""
    مرحبًا {user.first_name}!
    
    🤖 أهلاً بك في بوت الربح من الإعلانات!
    
    📌 يمكنك كسب المال عن طريق:
    1. مشاهدة الإعلانات
    2. دعوة الأصدقاء
    
    رابط الدعوة الخاص بك:
    {referral_link}
    """
    
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة ضغطات الأزرار"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if query.data == "balance":
        balance = db.get_user_balance(user_id)
        await query.edit_message_text(f"💰 رصيدك الحالي: {balance} وحدة")
    
    elif query.data == "view_ads":
        ads = db.get_active_ads()
        if ads:
            keyboard = []
            for ad in ads:
                keyboard.append([InlineKeyboardButton(ad['title'], callback_data=f"view_ad_{ad['ad_id']}")])
            
            keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("📢 اختر إعلانًا للمشاهدة:", reply_markup=reply_markup)
        else:
            await query.edit_message_text("⚠️ لا توجد إعلانات متاحة حاليًا.")
    
    elif query.data == "invite_friends":
        referral_link = f"https://t.me/{context.bot.username}?start=ref_{user_id}"
        referrals_count = db.get_user_referrals(user_id)
        
        message = f"""
        👥 دعوة الأصدقاء
        
        لكل صديق تدعوه وتحصل على 5 وحدات!
        
        رابط الدعوة الخاص بك:
        {referral_link}
        
        عدد الأصدقاء الذين دعوتهم: {referrals_count}
        """
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup)
    
    elif query.data == "back_to_main":
        await start(update, context)
    
    elif query.data.startswith("view_ad_"):
        ad_id = int(query.data[8:])
        ads = db.get_active_ads()
        ad = next((a for a in ads if a['ad_id'] == ad_id), None)
        
        if ad:
            db.add_ad_view(user_id, ad_id)
            db.update_balance(user_id, ad['reward'])
            
            message = f"""
            🎉 شكرًا لمشاهدتك الإعلان!
            
            📌 {ad['title']}
            {ad['description']}
            
            لقد حصلت على {ad['reward']} وحدات!
            """
            
            keyboard = [
                [InlineKeyboardButton("🔙 رجوع", callback_data="view_ads")],
                [InlineKeyboardButton("🏠 الرئيسية", callback_data="back_to_main")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, reply_markup=reply_markup)
        else:
            await query.edit_message_text("⚠️ عذرًا، هذا الإعلان لم يعد متاحًا.")

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """أوامر المدير"""
    user_id = update.effective_user.id
    if user_id != Config.ADMIN_ID:
        await update.message.reply_text("⚠️ ليس لديك صلاحية الوصول إلى هذا الأمر.")
        return
    
    if not context.args:
        await update.message.reply_text("""
        🛠 أوامر المدير:
        
        /add_ad العنوان - الوصف - الرابط - المكافأة
        /toggle_ad ad_id
        /user_info user_id
        """)
        return
    
    command = context.args[0].lower()
    
    if command == "add_ad" and len(context.args) >= 5:
        title = context.args[1]
        description = context.args[2]
        url = context.args[3]
        try:
            reward = float(context.args[4])
            with db.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                INSERT INTO ads (title, description, url, reward)
                VALUES (?, ?, ?, ?)
                ''', (title, description, url, reward))
                conn.commit()
            await update.message.reply_text(f"✅ تمت إضافة الإعلان: {title}")
        except ValueError:
            await update.message.reply_text("⚠️ المكافأة يجب أن تكون رقمًا.")
    
    elif command == "toggle_ad" and len(context.args) >= 2:
        try:
            ad_id = int(context.args[1])
            with db.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                UPDATE ads 
                SET is_active = NOT is_active 
                WHERE ad_id = ?
                ''', (ad_id,))
                conn.commit()
            await update.message.reply_text(f"✅ تم تغيير حالة الإعلان {ad_id}")
        except ValueError:
            await update.message.reply_text("⚠️ ad_id يجب أن يكون رقمًا.")
    
    elif command == "user_info" and len(context.args) >= 2:
        try:
            target_user_id = int(context.args[1])
            with db.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                SELECT * FROM users 
                WHERE user_id = ?
                ''', (target_user_id,))
                user = cursor.fetchone()
                
                cursor.execute('''
                SELECT COUNT(*) as referrals FROM referrals 
                WHERE inviter_id = ?
                ''', (target_user_id,))
                referrals = cursor.fetchone()['referrals']
                
            if user:
                message = f"""
                👤 معلومات المستخدم:
                
                🆔: {user['user_id']}
                👤: {user['first_name']} {user['last_name'] or ''}
                📛: @{user['username'] or 'N/A'}
                💰 الرصيد: {user['balance']}
                👥 عدد الدعوات: {referrals}
                📅 تاريخ الانضمام: {user['join_date']}
                """
                await update.message.reply_text(message)
            else:
                await update.message.reply_text("⚠️ المستخدم غير موجود.")
        except ValueError:
            await update.message.reply_text("⚠️ user_id يجب أن يكون رقمًا.")

def main() -> None:
    """تشغيل البوت"""
    # إنشاء جداول قاعدة البيانات إذا لم تكن موجودة
    db.init_db()
    
    # إضافة بعض الإعلانات الافتراضية إذا لم تكن موجودة
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) as count FROM ads')
        if cursor.fetchone()['count'] == 0:
            cursor.executemany('''
            INSERT INTO ads (title, description, url, reward)
            VALUES (?, ?, ?, ?)
            ''', [
                ("إعلان تجريبي 1", "هذا إعلان تجريبي للمستخدمين الجدد", "https://example.com", 1.5),
                ("إعلان تجريبي 2", "إعلان آخر لاختبار النظام", "https://example.com", 2.0),
            ])
            conn.commit()
    
    # إنشاء التطبيق
    application = Application.builder().token(Config.BOT_TOKEN).build()
    
    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # تشغيل البوت
    application.run_polling()

if __name__ == "__main__":
    main()
