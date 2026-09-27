import sqlite3
from urllib.parse import quote

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# =========================================================
# SETTINGS
# =========================================================

BOT_TOKEN = "8871401548:AAEkhpvVLWeBYzeZLBipq4zgu5JKKGL6PUA"

CHANNEL_USERNAME = "@KamaiKhoj"
CHANNEL_LINK = "https://t.me/KamaiKhoj"

REFERRAL_REWARD = 5
MIN_WITHDRAW = 50
MAX_WITHDRAW = 500

# अभी सिर्फ testing के लिए
TEST_MODE = True

DB_NAME = "refercashx.db"


# =========================================================
# DATABASE
# =========================================================

def db():
    return sqlite3.connect(DB_NAME)


def create_database():
    conn = db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            referrer_id INTEGER,
            balance INTEGER DEFAULT 0,
            total_earned INTEGER DEFAULT 0,
            total_withdrawn INTEGER DEFAULT 0,
            referrals INTEGER DEFAULT 0,
            joined INTEGER DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            referrer_id INTEGER,
            reward INTEGER DEFAULT 5
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            status TEXT DEFAULT 'TEST',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def save_user(user):
    conn = db()
    cur = conn.cursor()

    cur.execute("""
        INSERT OR IGNORE INTO users
        (user_id, username, first_name)
        VALUES (?, ?, ?)
    """, (
        user.id,
        user.username or "",
        user.first_name or ""
    ))

    cur.execute("""
        UPDATE users
        SET username = ?, first_name = ?
        WHERE user_id = ?
    """, (
        user.username or "",
        user.first_name or "",
        user.id
    ))

    conn.commit()
    conn.close()


def get_user(user_id):
    conn = db()
    cur = conn.cursor()

    cur.execute("""
        SELECT user_id, username, first_name, referrer_id,
               balance, total_earned, total_withdrawn,
               referrals, joined
        FROM users
        WHERE user_id = ?
    """, (user_id,))

    row = cur.fetchone()
    conn.close()

    return row


# =========================================================
# CHANNEL CHECK
# =========================================================

async def is_joined(bot, user_id):
    try:
        member = await bot.get_chat_member(
            chat_id=CHANNEL_USERNAME,
            user_id=user_id
        )

        return member.status in [
            "member",
            "administrator",
            "creator"
        ]

    except Exception:
        return False


# =========================================================
# KEYBOARDS
# =========================================================

def join_keyboard():
    keyboard = [
        [
            InlineKeyboardButton(
                "📢 Join Channel",
                url=CHANNEL_LINK
            )
        ],
        [
            InlineKeyboardButton(
                "✅ Claim",
                callback_data="claim"
            )
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


def main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton(
                "👤 Account",
                callback_data="account"
            ),
            InlineKeyboardButton(
                "👥 Invite Link",
                callback_data="invite"
            )
        ],
        [
            InlineKeyboardButton(
                "💰 Extra Cash",
                callback_data="extra"
            ),
            InlineKeyboardButton(
                "💸 Cashout",
                callback_data="cashout"
            )
        ],
        [
            InlineKeyboardButton(
                "📊 Report",
                callback_data="report"
            )
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


def back_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔙 Back",
                callback_data="home"
            )
        ]
    ])


# =========================================================
# WELCOME SCREEN
# =========================================================

async def show_join_screen(update, context, user_id):
    user = get_user(user_id)

    first_name = user[2] if user else "User"

    text = (
        f"👋 Welcome, {first_name}!\n\n"
        f"🤖 Welcome to ReferCashX\n\n"
        f"🆔 Your ID: `{user_id}`\n"
        f"📢 Required Channel: {CHANNEL_USERNAME}\n\n"
        f"👇 पहले हमारे channel को join करें।\n"
        f"फिर नीचे दिए गए Claim button को दबाएँ।\n\n"
        f"⚠️ Channel join किए बिना Claim complete नहीं होगा।"
    )

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=join_keyboard()
    )


# =========================================================
# /START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    save_user(user)

    user_id = user.id

    # Referral parameter
    referrer_id = None

    if context.args:
        try:
            referrer_id = int(context.args[0])
        except ValueError:
            referrer_id = None

    # Self referral रोकना
    if referrer_id == user_id:
        referrer_id = None

    conn = db()
    cur = conn.cursor()

    # अगर user का referrer पहले से नहीं है
    cur.execute(
        "SELECT referrer_id FROM users WHERE user_id = ?",
        (user_id,)
    )

    existing = cur.fetchone()

    if existing and existing[0] is None and referrer_id:

        # Referrer मौजूद है तो ही save करें
        cur.execute(
            "SELECT user_id FROM users WHERE user_id = ?",
            (referrer_id,)
        )

        referrer_exists = cur.fetchone()

        if referrer_exists:
            cur.execute("""
                UPDATE users
                SET referrer_id = ?
                WHERE user_id = ?
            """, (referrer_id, user_id))

    conn.commit()
    conn.close()

    # पहले से joined है?
    joined = await is_joined(
        context.bot,
        user_id
    )

    if joined:

        conn = db()
        cur = conn.cursor()

        cur.execute("""
            UPDATE users
            SET joined = 1
            WHERE user_id = ?
        """, (user_id,))

        conn.commit()
        conn.close()

        await update.message.reply_text(
            "🏠 Welcome back!\n\n"
            "नीचे से कोई option चुनें:",
            reply_markup=main_keyboard()
        )

    else:

        await show_join_screen(
            update,
            context,
            user_id
        )


# =========================================================
# CLAIM
# =========================================================

async def claim(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    user_id = query.from_user.id

    joined = await is_joined(context.bot, user_id)

    if not joined:
        try:
            await query.answer(text="Please join the channel first!", show_alert=True)
        except Exception:
            pass
        return
    # Referral information
    cur.execute("""
        SELECT referrer_id
        FROM users
        WHERE user_id = ?
    """, (user_id,))

    row = cur.fetchone()

    if row:
        referrer_id = row[0]
    else:
        referrer_id = None

    # Referral पहले credit हुआ या नहीं
    cur.execute("""
        SELECT id
        FROM referrals
        WHERE user_id = ?
    """, (user_id,))

    already_rewarded = cur.fetchone()

    if (
        referrer_id
        and not already_rewarded
        and referrer_id != user_id
    ):

        # Referrer मौजूद है?
        cur.execute("""
            SELECT user_id
            FROM users
            WHERE user_id = ?
        """, (referrer_id,))

        referrer_exists = cur.fetchone()

        if referrer_exists:

            cur.execute("""
                UPDATE users
                SET balance = balance + ?,
                    total_earned = total_earned + ?,
                    referrals = referrals + 1
                WHERE user_id = ?
            """, (
                REFERRAL_REWARD,
                REFERRAL_REWARD,
                referrer_id
            ))

            cur.execute("""
                INSERT INTO referrals
                (user_id, referrer_id, reward)
                VALUES (?, ?, ?)
            """, (
                user_id,
                referrer_id,
                REFERRAL_REWARD
            ))

    conn.commit()
    conn.close()

    # Join screen delete
    try:
        await query.message.delete()
    except Exception:
        pass

    # Main menu
    await context.bot.send_message(
        chat_id=user_id,
        text=(
            "🎉 Verification Successful!\n\n"
            "✅ Channel joined successfully.\n\n"
            "🏠 Main Menu\n"
            "नीचे से कोई option चुनें:"
        ),
        reply_markup=main_keyboard()
    )


# =========================================================
# HOME
# =========================================================

async def home(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    await query.edit_message_text(
        "🏠 Main Menu\n\n"
        "नीचे से कोई option चुनें:",
        reply_markup=main_keyboard()
    )


# =========================================================
# ACCOUNT
# =========================================================

async def account(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    user = get_user(user_id)

    if not user:
        return

    balance = user[4]
    earned = user[5]
    withdrawn = user[6]
    referrals = user[7]

    text = (
        "👤 YOUR ACCOUNT\n\n"
        f"🆔 User ID: `{user_id}`\n"
        f"💰 Balance: ₹{balance}\n"
        f"👥 Total Referrals: {referrals}\n"
        f"💵 Total Earned: ₹{earned}\n"
        f"💸 Total Withdrawn: ₹{withdrawn}\n"
    )

    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=back_keyboard()
    )


# =========================================================
# INVITE LINK
# =========================================================

async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    bot_info = await context.bot.get_me()

    bot_username = bot_info.username

    referral_link = (
        f"https://t.me/{bot_username}?start={user_id}"
    )

    share_text = quote(
        "ReferCashX पर join करो और referral system test करो!"
    )

    share_url = (
        f"https://t.me/share/url?"
        f"url={quote(referral_link)}&"
        f"text={share_text}"
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "📤 Share Link",
                url=share_url
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 Back",
                callback_data="home"
            )
        ]
    ]

    text = (
        "👥 REFER & EARN\n\n"
        "अपने दोस्तों को यह link भेजें:\n\n"
        f"`{referral_link}`\n\n"
        f"💰 हर valid referral = ₹{REFERRAL_REWARD}\n\n"
        "⚠️ अभी यह TEST MODE में है।"
    )

    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================================================
# EXTRA CASH
# =========================================================

async def extra(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    text = (
        "💰 EXTRA CASH\n\n"
        "Refer & Earn system के जरिए rewards मिलेंगे।\n\n"
        f"👥 हर valid referral: ₹{REFERRAL_REWARD}\n"
        f"💸 Minimum Cashout: ₹{MIN_WITHDRAW}\n"
        f"🔝 Maximum Cashout: ₹{MAX_WITHDRAW}\n\n"
        "📌 अभी पूरा system TEST MODE में है।"
    )

    await query.edit_message_text(
        text,
        reply_markup=back_keyboard()
    )


# =========================================================
# REPORT
# =========================================================

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    conn = db()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*)
        FROM withdrawals
        WHERE user_id = ?
    """, (user_id,))

    withdrawal_count = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM withdrawals
        WHERE user_id = ?
        AND status = 'TEST'
    """, (user_id,))

    test_count = cur.fetchone()[0]

    conn.close()

    text = (
        "📊 YOUR REPORT\n\n"
        f"💸 Cashout Requests: {withdrawal_count}\n"
        f"🧪 Test Requests: {test_count}\n\n"
        "Referral statistics देखने के लिए Account खोलें।"
    )

    await query.edit_message_text(
        text,
        reply_markup=back_keyboard()
    )


# =========================================================
# CASHOUT
# =========================================================

async def cashout(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    user = get_user(user_id)

    balance = user[4]

    if balance < MIN_WITHDRAW:

        await query.answer(
            f"Minimum cashout ₹{MIN_WITHDRAW} है।",
            show_alert=True
        )

        return

    context.user_data["cashout_step"] = "amount"

    await query.message.reply_text(
        "💸 CASHOUT\n\n"
        f"Available Balance: ₹{balance}\n\n"
        f"Minimum: ₹{MIN_WITHDRAW}\n"
        f"Maximum: ₹{MAX_WITHDRAW}\n\n"
        "Test cashout के लिए amount भेजें।\n"
        "Cancel करने के लिए /cancel लिखें।"
    )


# =========================================================
# TEXT HANDLER
# =========================================================

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    step = context.user_data.get("cashout_step")

    if step != "amount":
        return

    text = update.message.text.strip()

    try:
        amount = int(text)
    except ValueError:

        await update.message.reply_text(
            "❌ सिर्फ amount भेजें। उदाहरण: 50"
        )

        return

    user = get_user(user_id)

    balance = user[4]

    if amount < MIN_WITHDRAW:

        await update.message.reply_text(
            f"❌ Minimum cashout ₹{MIN_WITHDRAW} है।"
        )

        return

    if amount > MAX_WITHDRAW:

        await update.message.reply_text(
            f"❌ Maximum cashout ₹{MAX_WITHDRAW} है।"
        )

        return

    if amount > balance:

        await update.message.reply_text(
            "❌ आपके balance में इतना amount नहीं है।"
        )

        return

    # TEST withdrawal
    conn = db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO withdrawals
        (user_id, amount, status)
        VALUES (?, ?, 'TEST')
    """, (
        user_id,
        amount
    ))

    conn.commit()
    conn.close()

    context.user_data.pop("cashout_step", None)

    await update.message.reply_text(
        "🧪 TEST CASHOUT CREATED!\n\n"
        f"💰 Amount: ₹{amount}\n"
        "📌 Status: TEST\n\n"
        "⚠️ अभी कोई real payment नहीं भेजी गई है।"
    )


# =========================================================
# CANCEL
# =========================================================

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data.clear()

    await update.message.reply_text(
        "❌ Current process cancelled.\n\n"
        "🏠 Main Menu",
        reply_markup=main_keyboard()
    )


# =========================================================
# COMMAND: /ID
# =========================================================

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        f"🆔 Your Telegram ID:\n\n"
        f"`{update.effective_user.id}`",
        parse_mode="Markdown"
    )

0
# =========================================================
# BUTTON HANDLER
# =========================================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    if query.data == "claim":
        await claim(update, context)

    elif query.data == "home":
        await home(update, context)

    elif query.data == "account":
        await account(update, context)

    elif query.data == "invite":
        await invite(update, context)

    elif query.data == "extra":
        await extra(update, context)

    elif query.data == "cashout":
        await cashout(update, context)

    elif query.data == "report":
        await report(update, context)


# =========================================================
# MAIN
# =========================================================

def main():

    create_database()

    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("cancel", cancel)
    )

    app.add_handler(
        CommandHandler("id", get_id)
    )

    app.add_handler(
        CallbackQueryHandler(button_handler)
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_handler
        )
    )

    print("================================")
    print("ReferCashX Bot is running...")
    print("TEST MODE:", TEST_MODE)
    print("================================")

    app.run_polling()


if __name__ == "__main__":
    main()

