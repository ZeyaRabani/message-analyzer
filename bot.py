#!/usr/bin/env python3
"""
Telegram Message Analyzer Bot - Uses Groq (Free Tier)
Keys read from environment variables for security
"""

import os
import requests
from telegram import Update
from telegram.ext import Application, MessageHandler, filters

# ============================================
# CONFIGURATION - Read from Environment Variables
# ============================================

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
YOUR_USER_ID = int(os.environ.get("YOUR_USER_ID", "0"))

# Groq API endpoint
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# ============================================
# BOT LOGIC
# ============================================

async def analyze_message(update: Update, context):
    """Main function - analyzes messages sent to the bot"""
    
    user_id = update.effective_user.id
    message_text = update.message.text
    
    # Only respond to you
    if YOUR_USER_ID and user_id != YOUR_USER_ID:
        return
    
    await update.message.reply_text("🤔 Analyzing...")
    
    # Prompt for analysis
    prompt = f"""Analyze this Telegram message and provide exactly:

1. Relevance: (Yes/No/Maybe)
2. Summary: (max 15 words)
3. Urgency: (Low/Medium/High)
4. Action needed: (Yes/No)

Message: "{message_text}"

Keep response very short, under 200 characters."""
    
    # Call Groq API
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that analyzes messages concisely."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 200
    }
    
    try:
        response = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            analysis = result["choices"][0]["message"]["content"]
            await update.message.reply_text(f"📊 **Analysis:**\n{analysis}", parse_mode="Markdown")
        else:
            await update.message.reply_text(f"❌ API Error: {response.status_code}")
            print(f"Error: {response.text}")
            
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:100]}")
        print(f"Error: {e}")

async def start_command(update: Update, context):
    user_id = update.effective_user.id
    if YOUR_USER_ID and user_id != YOUR_USER_ID:
        await update.message.reply_text("Sorry, this bot is private.")
        return
    
    await update.message.reply_text(
        "✅ **Bot is running!**\n\n"
        "Forward any message to me for analysis.\n"
        "I will never reply in groups.\n\n"
        "Powered by: **Groq** (free tier)",
        parse_mode="Markdown"
    )

async def help_command(update: Update, context):
    user_id = update.effective_user.id
    if YOUR_USER_ID and user_id != YOUR_USER_ID:
        return
    
    await update.message.reply_text(
        "**How to use:**\n"
        "1. Forward a message from any group to me\n"
        "2. I'll analyze it privately\n"
        "3. You get a summary instantly",
        parse_mode="Markdown"
    )

def main():
    # Check required environment variables
    if not TELEGRAM_BOT_TOKEN:
        print("❌ ERROR: TELEGRAM_BOT_TOKEN environment variable not set!")
        return
    if not GROQ_API_KEY:
        print("❌ ERROR: GROQ_API_KEY environment variable not set!")
        return
    if YOUR_USER_ID == 0:
        print("❌ ERROR: YOUR_USER_ID environment variable not set!")
        return
    
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, analyze_message))
    app.add_handler(MessageHandler(filters.COMMAND & filters.Regex('^/start$'), start_command))
    app.add_handler(MessageHandler(filters.COMMAND & filters.Regex('^/help$'), help_command))
    
    print("✅ Bot is running with Groq!")
    print("Press Ctrl+C to stop.")
    app.run_polling()

if __name__ == "__main__":
    main()
