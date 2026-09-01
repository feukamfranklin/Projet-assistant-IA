import os

import telebot
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("Definissez TELEGRAM_BOT_TOKEN dans votre fichier .env avant de lancer le bot.")
RAG_API_URL = 'http://127.0.0.1:8000/chat'

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_text = message.text
    # Envoyer la question à votre API RAG
    response = requests.post(RAG_API_URL, json={"message": user_text, "num_tel": str(message.chat.id)})
    answer = response.json().get("answer", "Désolé, une erreur est survenue.")
    
    bot.reply_to(message, answer)

bot.infinity_polling()
