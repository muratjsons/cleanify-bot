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
        return None
    if not QA_DATA:
        return None
    for question, answer in QA_DATA.items():
        cleaned_question = re.sub(r'[^\w\s]', '', question.lower().strip())
        if cleaned_input == cleaned_question:
            return answer
        if any(keyword in cleaned_input for keyword in cleaned_question.split()):
            return answer
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
                    {"role": "system", "content": "You are a friendly and casual assistant for the Cleanify platform. Respond to casual greetings or questions in English with a polite, conversational tone, avoiding generic platform descriptions. Engage directly with the user's greeting or question (e.g.
