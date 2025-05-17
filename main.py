import json
import re
import logging
import asyncio
import os
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)
from telegram import Update
from openai import OpenAI

# Loglama ayarları
logging.basicConfig(
    filename='cleanify_bot.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# API ayarları (sabit anahtarlar kaldırılarak sadece ortam değişkeni kullanılıyor)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
    logging.error("TELEGRAM_TOKEN or OPENAI_API_KEY environment variables are not set!")
    raise ValueError("TELEGRAM_TOKEN or OPENAI_API_KEY environment variables are not set!")

openai_client = OpenAI(api_key=OPENAI_API_KEY)

# qa.json dosyasını yükle
def load_qa_json():
    try:
        print("Attempting to load qa.json...")
        with open("qa.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            logging.info("qa.json loaded successfully")
            print("Loaded QA_DATA:", data)
            if not data:
                print("Warning: QA_DATA is empty!")
            return data
    except FileNotFoundError:
        logging.error("qa.json file not found")
        print("qa.json file not found")
        return {}
    except json.JSONDecodeError as e:
        logging.error(f"JSON decode error in qa.json: {e}")
        print(f"JSON decode error in qa.json: {e}")
        return {}
    except Exception as e:
        logging.error(f"Error loading qa.json: {e}")
        print(f"Error loading qa.json: {e}")
        return {}

QA_DATA = load_qa_json()

# Soru eşleştirme fonksiyonu
def match_question(user_input):
    print("User input:", user_input)
    cleaned_input = re.sub(r'[^\w\s]', '', user_input.lower().strip().replace("/cleanify", "").strip())
    print("Cleaned input:", cleaned_input)
    if not QA_DATA:
        print("Error: QA_DATA is empty!")
        return None
    for question, answer in QA_DATA.items():
        cleaned_question = re.sub(r'[^\w\s]', '', question.lower().strip())
        print(f"Checking: {cleaned_question}")
        if any(keyword in cleaned_input for keyword in cleaned_question.split()):
            print(f"Match found for: {question}")
            return answer
    print("No match found")
    return None

# /cleanify komutu
async def cleanify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = " ".join(context.args) if context.args else ""
    if not user_message:
        await update.message.reply_text("Please provide a message after /cleanify. Example: /cleanify What is Cleanify?")
        return

    try:
        answer = match_question(user_message)
        if answer:
            await update.message.reply_text(answer)
            logging.info(f"Replied to: {user_message}")
        else:
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a text-refining bot for the Cleanify platform. Rewrite the user’s message to be more fluent, polite, and professional. Cleanify is a platform that helps track environmental cleanup efforts and rewards users with B3TR tokens."},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=150
            )
            cleaned_text = response.choices[0].message.content.strip()
            await update.message.reply_text(cleaned_text)
    except Exception as e:
        # Anahtarı loglarda gizlemek için maskele
        error_message = str(e).replace(OPENAI_API_KEY, '****').replace(TELEGRAM_TOKEN, '****')
        logging.error(f"An error occurred: {error_message}")
        await update.message.reply_text("An error occurred. Please contact the admin.")

# Botu başlat
def main():
    logging.info("Bot is starting...")
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("cleanify", cleanify))
    logging.info("Bot handlers are set.")
    app.run_polling(timeout=30)

if __name__ == "__main__":
    main()
