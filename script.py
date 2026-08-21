import asyncio
import random
import logging
import re
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import List

from telegram import Bot, Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram import ReactionTypeEmoji
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

# ============================================
# 🌐 Railway Keep-Alive Web Server (Railway Compatibility)
# ============================================
def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    class HealthCheckHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Telegram Reaction Bot is running successfully!")
        def log_message(self, format, *args):
            pass # লোগ ফাইল পরিষ্কার রাখার জন্য এক্সেস লগ বন্ধ রাখা হলো

    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    print(f"🌐 Railway Web Server started on port {port}")
    server.serve_forever()

# ব্যাকগ্রাউন্ডে ওয়েব সার্ভার রান করা হচ্ছে
threading.Thread(target=run_web_server, daemon=True).start()

# ============================================
# 📌 কনফিগারেশন — আপনার তথ্য এখানে বসান
# ============================================

MAIN_BOT_TOKEN = os.environ.get("MAIN_BOT_TOKEN", "8871727460:AAEl_Ss_xAspLtihqphwj7_ZQXKZ1r2bkVw")

# 🤖 চাইল্ড বট টোকেন লিস্ট (মোট ৬টি স্লট)
CHILD_BOT_TOKENS = [
    os.environ.get("CHILD_BOT_1", "8790061583:AAFzI2P6l_sAbyFsm3SaqIb00vZn3kpDtow"),  # চাইল্ড বট ১
    os.environ.get("CHILD_BOT_2", "8998253597:AAEfKJ4MsheIlfE9BZy8OUbld7nQ7xRN2Hg"),                           # চাইল্ড বট ২
    os.environ.get("CHILD_BOT_3", "8817261804:AAFEJH3nQolmYsrUeqlWuqvtq7WJLinMFtg"),                           # চাইল্ড বট ৩
    os.environ.get("CHILD_BOT_4", "8849735278:AAHH21mH7R6xXH1QJZBvEwS00QbbD2J9Zk4"),                           # চাইল্ড বট ৪
    os.environ.get("CHILD_BOT_5", "8736166588:AAHHmEXYKEsJYIQ-vBxyPbpelY42cNtctUY"),                           # চাইল্ড বট ৫ (নতুন)
    os.environ.get("CHILD_BOT_6", "8964912183:AAFBKIYZVY9Ut6nxRHXFRUW8eJ9O2S-F1hA"),                           # চাইল্ড বট ৬ (নতুন)
]

# 🔐 আপনার টেলিগ্রাম অ্যাডমিন আইডি এখানে বসান
ADMIN_USER_ID = int(os.environ.get("ADMIN_USER_ID", 6620965115))  # <-- আপনার রিয়েল টেলিগ্রাম আইডি এখানে দিন

# ============================================
# ⚙️ কনভার্সেশন স্টেটস (ধাপসমূহ)
# ============================================
GET_LINKS, GET_EMOJI_TABLE, GET_DURATION = range(3)

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

class ReactionEngine:
    def __init__(self):
        self.child_bots: List[Bot] = [Bot(t) for t in CHILD_BOT_TOKENS if not t.endswith("_TOKEN_HERE")]
        self.main_bot = Bot(MAIN_BOT_TOKEN)
        logger.info(f"✅ সফলভাবে {len(self.child_bots)}টি চাইল্ড বট লোড হয়েছে")
    
    async def resolve_link(self, text: str):
        match = re.search(r't\.me/([a-zA-Z0-9_]+)/(\d+)', text.strip())
        if match:
            return match.group(1), int(match.group(2))
        return None, None

    async def drip_react_campaign(self, chat_id: int, message_ids: list, emoji_list: list, duration_minutes: float):
        total_bots_available = len(self.child_bots)
        total_delay_seconds = duration_minutes * 60
        
        reactions_per_post = len(emoji_list)
        total_actions = len(message_ids) * reactions_per_post
        
        delay_per_action = total_delay_seconds / total_actions if total_actions > 0 else 0

        logger.info(f"🚀 ক্যাম্পেইন শুরু: {len(message_ids)}টি পোস্ট, প্রতিটিতে রিঅ্যাকশন সংখ্যা: {reactions_per_post}, সময়: {duration_minutes} মিনিট।")

        for msg_id in message_ids:
            current_emojis = emoji_list.copy()
            random.shuffle(current_emojis)
            
            for i, emoji in enumerate(current_emojis):
                if i >= total_bots_available:
                    break
                
                bot = self.child_bots[i]
                try:
                    reaction_obj = ReactionTypeEmoji(emoji=emoji)
                    await bot.set_message_reaction(
                        chat_id=chat_id,
                        message_id=msg_id,
                        reaction=[reaction_obj]
                    )
                    logger.info(f"✅ সফল: Chat ID {chat_id}, Post {msg_id} -> {emoji}")
                except Exception as e:
                    logger.error(f"❌ Error on post {msg_id}: {e}")
                
                if delay_per_action > 0:
                    await asyncio.sleep(delay_per_action)

engine = ReactionEngine()

# ============================================
# ⌨️ রিপ্লাই কিবোর্ড ডিজাইন
# ============================================
def get_main_keyboard():
    return ReplyKeyboardMarkup(
        [["🔗 পোস্ট লিংক"]],
        resize_keyboard=True
    )

def get_cancel_keyboard():
    return ReplyKeyboardMarkup(
        [["❌ বাতিল করুন"]],
        resize_keyboard=True
    )

# বর্ধিত ও সাজানো ইমোজি সিলেকশন টেবিল (ইনলাইন কিবোর্ড) জেনারেটর
def get_emoji_table_markup(selected_emojis: list):
    max_slots = len(engine.child_bots)
    summary_text = " ".join(selected_emojis) if selected_emojis else "কোনোটি নির্বাচন করা হয়নি"
    
    keyboard = [
        [
            InlineKeyboardButton("👍 লাইক (+1)", callback_data="add_thumb"),
            InlineKeyboardButton("❤️ লাভ (+1)", callback_data="add_heart"),
            InlineKeyboardButton("🔥 ফায়ার (+1)", callback_data="add_fire")
        ],
        [
            InlineKeyboardButton("👏 ক্ল্যাপ (+1)", callback_data="add_clap"),
            InlineKeyboardButton("😂 হাসি (+1)", callback_data="add_laugh"),
            InlineKeyboardButton("🎉 পার্টি (+1)", callback_data="add_party")
        ],
        [
            InlineKeyboardButton("🤔 ভাবছি (+1)", callback_data="add_thinking"),
            InlineKeyboardButton("💯 ১০০ (+1)", callback_data="add_100"),
            InlineKeyboardButton("🤩 ওয়াও (+1)", callback_data="add_star")
        ],
        [
            InlineKeyboardButton("😢 স্যাড (+1)", callback_data="add_sad"),
            InlineKeyboardButton("🚀 রকেট (+1)", callback_data="add_rocket"),
            InlineKeyboardButton("🙏 দোয়া (+1)", callback_data="add_pray")
        ],
        [
            InlineKeyboardButton("🤯 মাথা নষ্ট (+1)", callback_data="add_mindblown"),
            InlineKeyboardButton("👀 চোখ (+1)", callback_data="add_eyes")
        ],
        [
            InlineKeyboardButton("🔄 রিসেট", callback_data="reset_emojis"),
            InlineKeyboardButton("✅ কনফার্ম", callback_data="confirm_emojis")
        ]
    ]
    return InlineKeyboardMarkup(keyboard), summary_text

# ============================================
# 🛡️ সিকিউরিটি চেক ফাংশন
# ============================================
def is_admin(update: Update) -> bool:
    user = update.effective_user
    if user and user.id == ADMIN_USER_ID:
        return True
    return False

# ============================================
# 🎛️ কনভার্সেশন হ্যান্ডলার (ফ্লো লজিক)
# ============================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("❌ আপনার এই বট ব্যবহারের অনুমতি নেই। এটি শুধুমাত্র অ্যাডমিনের জন্য সংরক্ষিত।")
        return ConversationHandler.END

    await update.message.reply_text(
        "🤖 *অটো রিঅ্যাকশন কন্ট্রোল প্যানেলে স্বাগতম!*\n\n"
        "নিচের কিবোর্ড থেকে **🔗 পোস্ট লিংক** বাটনে ক্লিক করে কাজ শুরু করুন:",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )
    return ConversationHandler.END

async def ask_for_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return ConversationHandler.END

    await update.message.reply_text(
        "🔗 **ধাপ ১/৩: পোস্টের লিংক দিন**\n\n"
        "একাধিক লিংক দিতে চাইলে প্রতি লাইনে একটি করে পোস্টের লিংক দিন:\n"
        "যেমন:\n"
        "`https://t.me/YourChannel/10`\n"
        "`https://t.me/YourChannel/11`",
        reply_markup=get_cancel_keyboard(),
        parse_mode="Markdown"
    )
    return GET_LINKS

async def receive_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return ConversationHandler.END

    text = update.message.text.strip()
    if text == "❌ বাতিল করুন":
        return await cancel(update, context)

    lines = text.split("\n")
    valid_links = []
    channel_name = None
    chat_id = None
    
    for line in lines:
        channel, post_id = await engine.resolve_link(line)
        if channel and post_id:
            if not chat_id:
                try:
                    chat_info = await engine.main_bot.get_chat(f"@{channel}")
                    chat_id = chat_info.id
                    channel_name = channel
                except Exception as e:
                    await update.message.reply_text(f"❌ চ্যানেল খুঁজে পাওয়া যায়নি বা বট অ্যাডমিন নেই: @{channel}")
                    return GET_LINKS
            valid_links.append(post_id)
            
    if not valid_links:
        await update.message.reply_text("❌ কোনো বৈধ টেলিগ্রাম পোস্টের লিংক পাওয়া যায়নি। সঠিক ফরম্যাটে আবার লিংক দিন:")
        return GET_LINKS
        
    context.user_data['chat_id'] = chat_id
    context.user_data['channel_name'] = channel_name
    context.user_data['post_ids'] = valid_links
    context.user_data['selected_emojis'] = []
    
    markup, summary = get_emoji_table_markup(context.user_data['selected_emojis'])
    
    await update.message.reply_text(
        f"✅ মোট **{len(valid_links)}টি** পোস্ট সফলভাবে যুক্ত হয়েছে!\n\n"
        f"🎛️ **ধাপ ২/৩: ইমোজি সিলেকশন টেবিল**\n"
        f"নিচের বোতামগুলোতে ক্লিক করে আপনার পছন্দমতো ইমোজি যোগ করুন (সর্বোচ্চ {len(engine.child_bots)}টি):\n\n"
        f"📌 **বর্তমান সিলেকশন:** {summary}",
        reply_markup=markup,
        parse_mode="Markdown"
    )
    return GET_EMOJI_TABLE

async def handle_emoji_table(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    selected = context.user_data.get('selected_emojis', [])
    max_bots = len(engine.child_bots)
    
    emoji_mapping = {
        "add_thumb": "👍",
        "add_heart": "❤",
        "add_fire": "🔥",
        "add_clap": "👏",
        "add_laugh": "😂",
        "add_party": "🎉",
        "add_thinking": "🤔",
        "add_100": "💯",
        "add_star": "🤩",
        "add_sad": "😢",
        "add_rocket": "🚀",
        "add_pray": "🙏",
        "add_mindblown": "🤯",
        "add_eyes": "👀"
    }
    
    if data in emoji_mapping:
        if len(selected) < max_bots:
            selected.append(emoji_mapping[data])
        else:
            await query.answer(f"⚠️ আপনার সক্রিয় চাইল্ড বট মাত্র {max_bots}টি, এর বেশি যোগ করা যাবে না!", show_alert=True)
    elif data == "reset_emojis":
        selected.clear()
    elif data == "confirm_emojis":
        if not selected:
            await query.answer("❌ অন্তত একটি ইমোজি সিলেক্ট করুন!", show_alert=True)
            return GET_EMOJI_TABLE
        
        await query.message.edit_text(
            f"✅ ইমোজি কনফার্ম করা হয়েছে: {' '.join(selected)}\n\n"
            f"⏱️ **ধাপ ৩/৩: সময় নির্ধারণ করুন (Drip-feed)**\n"
            f"কত মিনিটের মধ্যে রিঅ্যাকশনগুলো সম্পূর্ণ দিতে চান? (ইনস্ট্যান্ট দিতে চাইলে `0` লিখুন):\n"
            f"*(যেমন: 5 লিখলে ৫ মিনিট ধরে ধীরে ধীরে রিঅ্যাকশনগুলো পড়বে)*",
            parse_mode="Markdown"
        )
        return GET_DURATION

    context.user_data['selected_emojis'] = selected
    markup, summary = get_emoji_table_markup(selected)
    
    try:
        await query.message.edit_text(
            f"🎛️ **ধাপ ২/৩: ইমোজি সিলেকশন টেবিল**\n"
            f"নিচের বোতামগুলোতে ক্লিক করে আপনার পছন্দমতো ইমোজি যোগ করুন (সর্বোচ্চ {max_bots}টি):\n\n"
            f"📌 **বর্তমান সিলেকশন:** {summary}",
            reply_markup=markup,
            parse_mode="Markdown"
        )
    except Exception:
        pass
        
    return GET_EMOJI_TABLE

async def receive_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return ConversationHandler.END

    text = update.message.text.strip()
    if text == "❌ বাতিল করুন":
        return await cancel(update, context)

    try:
        duration = float(text)
        if duration < 0:
            raise ValueError()
    except ValueError:
        await update.message.reply_text("❌ দয়া করে সঠিক সময় লিখুন (যেমন: 0 বা 5)।")
        return GET_DURATION
        
    chat_id = context.user_data['chat_id']
    channel_name = context.user_data['channel_name']
    post_ids = context.user_data['post_ids']
    emoji_list = context.user_data['selected_emojis']
    
    await update.message.reply_text(
        f"🎯 **ক্যাম্পেইন সফলভাবে শিডিউল করা হয়েছে!**\n\n"
        f"📢 চ্যানেল: @{channel_name}\n"
        f"📦 মোট পোস্ট: {len(post_ids)}টি\n"
        f"❤️ নির্বাচিত ইমোজি: {' '.join(emoji_list)} (মোট {len(emoji_list)}টি)\n"
        f"⏳ সময়কাল: {duration} মিনিট\n\n"
        f"বট ব্যাকগ্রাউন্ডে কাজ শুরু করে দিয়েছে! ✅",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )
    
    asyncio.create_task(
        engine.drip_react_campaign(chat_id, post_ids, emoji_list, duration)
    )
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return ConversationHandler.END
    await update.message.reply_text(
        "❌ ক্যাম্পেইন বাতিল করা হয়েছে। নতুন করে শুরু করতে নিচের **🔗 পোস্ট লিংক** বাটনে ক্লিক করুন:",
        reply_markup=get_main_keyboard()
    )
    return ConversationHandler.END

# ============================================
# 🚀 মেইন ফাংশন
# ============================================
def main():
    app = Application.builder().token(MAIN_BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.Regex("^🔗 পোস্ট লিংক$") & filters.TEXT, ask_for_links)
        ],
        states={
            GET_LINKS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_links)],
            GET_EMOJI_TABLE: [CallbackQueryHandler(handle_emoji_table, pattern="^(add_|reset_emojis|confirm_emojis)")],
            GET_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_duration)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    app.add_handler(conv_handler)
    
    logger.info("🤖 ৬টি চাইল্ড বট ও রেলওয়ে কমপ্যাটিবল রিঅ্যাকশন বট সফলভাবে চালু হয়েছে!")
    app.run_polling()

if __name__ == "__main__":
    main()
