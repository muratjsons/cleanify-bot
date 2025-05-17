import json
import re
import logging
import asyncio
import os
import difflib
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)
from telegram import Update
from openai import OpenAI

logging.basicConfig(
    filename='cleanify_bot.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
    logging.error("TELEGRAM_TOKEN or OPENAI_API_KEY environment variables are not set!")
    raise ValueError("TELEGRAM_TOKEN or OPENAI_API_KEY environment variables are not set!")

openai_client = OpenAI(api_key=OPENAI_API_KEY)

def load_qa_json():
    try:
        with open("qa.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            logging.info("qa.json loaded successfully")
            if not data:
                logging.warning("QA_DATA is empty!")
            return data
    except FileNotFoundError:
        logging.error("qa.json file not found")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"JSON decode error in qa.json: {e}")
        return None
    except Exception as e:
        logging.error(f"Error loading qa.json: {e}")
        return None

QA_DATA = load_qa_json()

CASUAL_MESSAGES = [
    "hi", "hello", "hey", "how are you", "good morning", "good afternoon", 
    "good evening", "good night", "goodnight", "bye", "see you", "how’s it going",
    "what’s up", "how you doing", "howdy", "greetings", "hey there", "hola",
    "ciao", "salut", "yo", "what's good", "take care", "catch you later",
    "see ya", "later", "night", "morning", "evening", "afternoon", "cheers",
    "thanks", "thank you", "nice to meet you", "how’s your day", "have a nice day"
]

def match_question(user_input):
    cleaned_input = re.sub(r'[^\w\s]', '', user_input.lower().strip().replace("/cleanify", "").strip())
    if QA_DATA is None:
        logging.error("QA_DATA is None")
        return None
    if not QA_DATA:
        logging.error("QA_DATA is empty")
        return None

    best_match = None
    best_score = 0.0
    threshold = 0.6  # Eşleşme skoru için eşik değeri (%60 benzerlik)

    for question, answer in QA_DATA.items():
        cleaned_question = re.sub(r'[^\w\s]', '', question.lower().strip())
        # difflib ile benzerlik skoru hesapla
        similarity_score = difflib.SequenceMatcher(None, cleaned_input, cleaned_question).ratio()
        logging.info(f"Comparing '{cleaned_input}' with '{cleaned_question}' - Similarity score: {similarity_score}")

        if similarity_score > best_score:
            best_score = similarity_score
            best_match = (question, answer)

        # Tam eşleşme kontrolü
        if cleaned_input == cleaned_question:
            logging.info(f"Exact match found for: {cleaned_input}")
            return answer
        # Kısmi eşleşme kontrolü (eski yöntem, yedek)
        if any(keyword in cleaned_input for keyword in cleaned_question.split()):
            logging.info(f"Partial match found for: {cleaned_input} with question: {cleaned_question}")
            return answer

    # En iyi eşleşme skoru eşiğin üzerindeyse, en iyi eşleşmeyi döndür
    if best_score >= threshold and best_match:
        logging.info(f"Best match found for: {cleaned_input} with question: {best_match[0]} (score: {best_score})")
        return best_match[1]

    logging.info(f"No match found for: {cleaned_input}")
    return None

def is_cleanify_related(user_input):
    cleanify_keywords = ["cleanify", "b3tr", "cleanup", "environmental", "tokens", "reward", "organize", "event", "group"]
    cleaned_input = user_input.lower().strip().replace("/cleanify", "").strip()
    return any(keyword in cleaned_input for keyword in cleanify_keywords)

def is_casual_message(user_input):
    cleaned_input = user_input.lower().strip().replace("/cleanify", "").strip()
    if any(cleaned_input == msg for msg in CASUAL_MESSAGES):
        return True
        return any(msg in cleaned_input for msg in CASUAL_MESSAGES)

async def cleanify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = " ".join(context.args) if context.args else ""
    if not user_message:
        await update.message.reply_text("Please provide a message after /cleanify. Example: /cleanify What is Cleanify?")
        return

    try:
        if QA_DATA is None:
            await update.message.reply_text("Sorry, I couldn't load the FAQ data. Please try again later or contact the admin.")
            logging.error("Failed to load QA_DATA for user request")
            return

        if is_casual_message(user_message):
            logging.info(f"Casual message detected: {user_message}")
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a friendly and casual assistant for the Cleanify platform. Respond to casual greetings or questions in English with a polite, conversational tone, avoiding generic platform descriptions. Engage directly with the user's greeting or question (e.g., 'Hi!' or 'How are you?') and subtly steer towards Cleanify-related topics like cleanup efforts or B3TR tokens. Cleanify is a platform that helps track environmental cleanup efforts and rewards users with B3TR tokens."},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=150
            )
            cleaned_text = response.choices[0].message.content.strip()
            await update.message.reply_text(cleaned_text)
            logging.info(f"Replied to casual message: {user_message} with: {cleaned_text}")
            return

        answer = match_question(user_message)
        if answer:
            await update.message.reply_text(answer)
            logging.info(f"Replied to: {user_message} with FAQ answer: {answer}")
            return

        if not is_cleanify_related(user_message):
            await update.message.reply_text("I can only respond to questions related to Cleanify. What would you like to know about Cleanify?")
            logging.info(f"Non-Cleanify message detected: {user_message}")
            return

        logging.info(f"No FAQ match for: {user_message}, querying OpenAI...")
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a text-refining bot for the Cleanify platform. Rewrite the user’s message to be more fluent, polite, and professional in English. Provide detailed guidance for specific questions like organizing events or earning tokens. Cleanify is a platform that helps track environmental cleanup efforts and rewards users with B3TR tokens."},
                {"role": "user", "content": user_message}
            ],
            max_tokens=200
        )
        cleaned_text = response.choices[0].message.content.strip()
        await update.message.reply_text(cleaned_text)
        logging.info(f"Replied to: {user_message} with OpenAI response: {cleaned_text}")

    except Exception as e:
        error_message = str(e).replace(OPENAI_API_KEY, '****').replace(TELEGRAM_TOKEN, '****')
        logging.error(f"An error occurred while processing {user_message}: {error_message}")
        await update.message.reply_text("An error occurred while processing your request. Please try again later or contact the admin.")

def main():
    logging.info("Bot is starting...")
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("cleanify", cleanify))
    logging.info("Bot handlers are set.")
    app.run_polling(timeout=30)

if __name__ == "__main__":
    main()
