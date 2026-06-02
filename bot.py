#!/usr/bin/env python3
"""
Telegram Message Analyzer Bot - Batch summarizer with name/company tracking
PUBLIC VERSION - anyone can use
"""

import os
import requests
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import Application, MessageHandler, filters

# ============================================
# CONFIGURATION
# ============================================

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Keywords to track (case insensitive)
KEYWORDS = ["BIT10", "bit10", "Bit10", "Zeya", "zeya"]

# Store messages temporarily (per user) - each user has their own queue
user_messages = {}

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# ============================================
# WEB SERVER FOR RENDER HEALTH CHECKS
# ============================================

web_app = Flask('')

@web_app.route('/')
def home():
    return "Bot is alive!"

def run_web():
    web_app.run(host='0.0.0.0', port=10000)

Thread(target=run_web, daemon=True).start()

# ============================================
# BOT LOGIC - PUBLIC VERSION (Anyone can use)
# ============================================

async def analyze_message(update: Update, context):
    """Store messages for batch processing - works for ANY user"""
    
    user_id = update.effective_user.id
    message_text = update.message.text
    
    # Store messages for THIS user (each user has their own queue)
    if user_id not in user_messages:
        user_messages[user_id] = []
    
    user_messages[user_id].append(message_text)
    
    count = len(user_messages[user_id])
    await update.message.reply_text(f"📥 Message stored. You have {count} message(s) in queue.\n\nSend /summarize to process all, or /clear to reset.")

async def summarize_command(update: Update, context):
    """Summarize all stored messages for the user"""
    
    user_id = update.effective_user.id
    
    if user_id not in user_messages or not user_messages[user_id]:
        await update.message.reply_text("📭 No messages stored. Send me messages first!")
        return
    
    messages = user_messages[user_id]
    await update.message.reply_text(f"📊 Processing {len(messages)} messages... This may take a moment.")
    
    # Check for keyword mentions
    mentions = []
    for msg in messages:
        for keyword in KEYWORDS:
            if keyword.lower() in msg.lower():
                mentions.append(f"• {keyword} found: \"{msg[:100]}...\"")
                break
    
    # Prepare batch for summarization
    combined = "\n---\n".join([f"Message {i+1}: {m}" for i, m in enumerate(messages)])
    
    prompt = f"""You are analyzing {len(messages)} messages.

TASK 1: Check if BIT10 or Zeya is mentioned. If yes, FLAG it as IMPORTANT.

TASK 2: Provide a 2-paragraph summary of ALL messages (key topics, themes).

Format your response EXACTLY like this:

🔴 **IMPORTANT MENTIONS:** (list any messages mentioning BIT10 or Zeya, or say "None")

📋 **SUMMARY:**
(paragraph 1 - main themes)
(paragraph 2 - key takeaways)

Here are the messages:
{combined}

Keep summaries concise and actionable."""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 800
    }
    
    try:
        response = requests.post(GROQ_URL, headers=headers, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            analysis = result["choices"][0]["message"]["content"]
            
            # Also create a separate mention alert
            if mentions:
                mention_alert = "\n".join(mentions)
                await update.message.reply_text(f"🔔 **BIT10/ZEYA ALERT!**\n{mention_alert}", parse_mode="Markdown")
            
            await update.message.reply_text(f"📊 **Batch Summary ({len(messages)} messages)**\n\n{analysis}", parse_mode="Markdown")
            
            # Clear messages after processing
            user_messages[user_id] = []
            
        else:
            await update.message.reply_text(f"❌ API Error: {response.status_code}")
            
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:100]}")

async def clear_command(update: Update, context):
    """Clear all stored messages for the user"""
    
    user_id = update.effective_user.id
    
    if user_id in user_messages:
        count = len(user_messages[user_id])
        user_messages[user_id] = []
        await update.message.reply_text(f"🗑️ Cleared {count} stored messages.")
    else:
        await update.message.reply_text("📭 No messages to clear.")

async def status_command(update: Update, context):
    """Show current message count for the user"""
    
    user_id = update.effective_user.id
    count = len(user_messages.get(user_id, []))
    await update.message.reply_text(f"📊 You have {count} message(s) in queue.\n\nSend /summarize to process, /clear to reset.")

async def start_command(update: Update, context):
    """Welcome message - now public"""
    await update.message.reply_text(
        "✅ **Batch Message Analyzer Active!**\n\n"
        "**How to use:**\n"
        "1. Forward any message to me throughout the day\n"
        "2. At end of day, send /summarize\n"
        "3. I'll tell you if BIT10 or Zeya was mentioned\n"
        "4. I'll summarize everything in 1-2 paragraphs\n\n"
        "**Commands:**\n"
        "/summarize - Process all stored messages\n"
        "/status - Show how many messages stored\n"
        "/clear - Delete all stored messages\n"
        "/help - Show this message",
        parse_mode="Markdown"
    )

async def help_command(update: Update, context):
    await start_command(update, context)

def main():
    if not TELEGRAM_BOT_TOKEN or not GROQ_API_KEY:
        print("❌ Missing environment variables!")
        return
    
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, analyze_message))
    app.add_handler(MessageHandler(filters.COMMAND & filters.Regex('^/start$'), start_command))
    app.add_handler(MessageHandler(filters.COMMAND & filters.Regex('^/help$'), help_command))
    app.add_handler(MessageHandler(filters.COMMAND & filters.Regex('^/summarize$'), summarize_command))
    app.add_handler(MessageHandler(filters.COMMAND & filters.Regex('^/clear$'), clear_command))
    app.add_handler(MessageHandler(filters.COMMAND & filters.Regex('^/status$'), status_command))
    
    print("✅ PUBLIC batch analyzer bot is running!")
    print("Anyone can use it now.")
    app.run_polling()

if __name__ == "__main__":
    main()
