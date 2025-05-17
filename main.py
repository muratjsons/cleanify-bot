import json
import re
import os
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update
from openai import OpenAI

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
    raise ValueError("TELEGRAM_TOKEN or OPENAI_API_KEY environment variables are not set!")

openai_client = OpenAI(api_key=OPENAI_API_KEY)

def load_qa_json():
    try:
        with open("qa.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            if not data or not data.get("questions"):
                return None
            return data
    except (FileNotFoundError, json.JSONDecodeError, Exception):
        return None

QA_DATA = load_qa_json()

CASUAL_MESSAGES = ["hi", "hello", "hey", "how are you", "good morning", "good afternoon", 
                  "good evening", "good night", "goodnight", "bye", "see you", "how’s it going",
                  "what’s up", "how you doing", "howdy", "greetings", "hey there", "hola",
                  "ciao", "salut", "yo", "what's good", "take care", "catch you later",
                  "see ya", "later", "night", "morning", "evening", "afternoon", "cheers",
                  "thanks", "thank you", "nice to meet you", "how’s your day", "have a nice day"]

def match_question(user_input):
    cleaned_input = re.sub(r'[^\w\s]', '', user_input.lower().strip().replace("/cleanify", "").strip())
    if not QA_DATA or not QA_DATA.get("questions"):
        return None

    best_match = None
    best_keyword_count = 0

    for question_set in QA_DATA["questions"]:
        for variation in question_set["variations"]:
            cleaned_variation = re.sub(r'[^\w\s]', '', variation.lower().strip())
            if cleaned_input == cleaned_variation:
                return question_set["answer"]

        keyword_count = sum(1 for keyword in question_set["keywords"] if keyword in cleaned_input)
        if keyword_count > best_keyword_count:
            best_keyword_count = keyword_count
            best_match = question_set["answer"]

    if best_match and best_keyword_count > 0:
        return best_match
    return None

def is_cleanify_related(user_input):
    cleanify_keywords = ["cleanify", "b3tr", "cleanup", "environmental", "tokens", "reward", "organize", "event", "group", "campaign"]
    cleaned_input = user_input.lower().strip().replace("/cleanify", "").strip()
    return any(keyword in cleaned_input for keyword in cleanify_keywords)

def is_casual_message(user_input):
    cleaned_input = user_input.lower().strip().replace("/cleanify", "").strip()
    return any(cleaned_input == msg or msg in cleaned_input for msg in CASUAL_MESSAGES)

async def cleanify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = " ".join(context.args) if context.args else ""
    if not user_message:
        await update.message.reply_text("Please provide a message after /cleanify. Example: /cleanify What is Cleanify?")
        return

    try:
        if not QA_DATA:
            await update.message.reply_text("Sorry, I couldn't load the FAQ data. Please try again later or contact the admin.")
            return

        if is_casual_message(user_message):
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a friendly and casual assistant for the Cleanify platform. Respond to casual greetings or questions in English with a polite, conversational tone. Engage directly with the user's greeting or question and subtly steer towards Cleanify-related topics like cleanup efforts or B3TR tokens."},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=150
            )
            await update.message.reply_text(response.choices[0].message.content.strip())
            return

        answer = match_question(user_message)
        if answer:
            await update.message.reply_text(answer)
            return

        if not is_cleanify_related(user_message):
            await update.message.reply_text("I can only respond to questions related to Cleanify. What would you like to know about Cleanify?")
            return

        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a text-refining bot for the Cleanify platform. Rewrite the user’s message to be more fluent, polite, and professional in English. Provide detailed guidance for specific questions like organizing events or earning tokens."},
                {"role": "user", "content": user_message}
            ],
            max_tokens=200
        )
        await update.message.reply_text(response.choices[0].message.content.strip())

    except Exception as e:
        await update.message.reply_text("An error occurred while processing your request. Please try again later or contact the admin.")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("cleanify", cleanify))
    app.run_polling(timeout=30)

if __name__ == "__main__":
    main()
