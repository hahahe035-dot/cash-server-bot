import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# Database setup
conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    status TEXT
)
""")
conn.commit()

# Start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("🇸🇾 عربي", callback_data="lang_ar"),
            InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
        ]
    ]
    await update.message.reply_text(
        "اختر اللغة / Choose Language",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Language selection
async def language_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "lang_ar":
        text = "اختر الخدمة:"
        button = "طلب خدمة"
    else:
        text = "Choose service:"
        button = "Order Service"

    keyboard = [[InlineKeyboardButton(button, callback_data="order")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# Create order
async def create_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    cursor.execute(
        "INSERT INTO orders (user_id, username, status) VALUES (?, ?, ?)",
        (user.id, user.username, "pending")
    )
    conn.commit()

    order_id = cursor.lastrowid

    await query.edit_message_text(
        f"🧾 رقم طلبك: {order_id}\n\n"
        f"قم بالدفع عبر كاش بلس ثم أرسل صورة الإشعار."
    )

# Receive payment proof
async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    cursor.execute(
        "SELECT id FROM orders WHERE user_id=? AND status='pending' ORDER BY id DESC LIMIT 1",
        (user.id,)
    )
    order = cursor.fetchone()

    if order:
        order_id = order[0]
        cursor.execute(
            "UPDATE orders SET status='review' WHERE id=?",
            (order_id,)
        )
        conn.commit()

        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=update.message.photo[-1].file_id,
            caption=f"طلب رقم {order_id} من @{user.username}"
        )

        await update.message.reply_text("تم إرسال الطلب للمراجعة.")
    else:
        await update.message.reply_text("لا يوجد طلب معلق.")

# Admin approve
async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    try:
        order_id = int(context.args[0])
        cursor.execute(
            "UPDATE orders SET status='approved' WHERE id=?",
            (order_id,)
        )
        conn.commit()
        await update.message.reply_text("تمت الموافقة.")
    except:
        await update.message.reply_text("اكتب: /approve رقم_الطلب")

# Main
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(language_handler, pattern="lang_"))
app.add_handler(CallbackQueryHandler(create_order, pattern="order"))
app.add_handler(MessageHandler(filters.PHOTO, receive_photo))
app.add_handler(CommandHandler("approve", approve))

app.run_polling()
