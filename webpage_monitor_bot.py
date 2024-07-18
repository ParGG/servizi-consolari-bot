import os
import requests
import hashlib
import telegram
from telegram.ext import Updater, CommandHandler, Dispatcher
from bs4 import BeautifulSoup
from flask import Flask, request
import threading

# Read secrets from environment variables
bot_token = os.environ['TELEGRAM_BOT_TOKEN']
chat_id = os.environ['TELEGRAM_CHAT_ID']
login_url = os.environ['LOGIN_URL']
target_url = os.environ['TARGET_URL']
credentials = {
    'username': os.environ['USERNAME'],
    'password': os.environ['PASSWORD']
}

# Function to start a session and log in
def start_session(login_url, credentials):
    session = requests.Session()
    session.post(login_url, data=credentials)
    return session

# Function to get the current content of the webpage
def get_page_content(session, url):
    response = session.get(url)
    return response.text

# Function to extract specific content from the webpage
def extract_content(html):
    soup = BeautifulSoup(html, 'html.parser')
    element = soup.select_one('#main > div.table-container')
    return element.get_text(strip=True) if element else "Element not found"

# Function to compute the hash of the content
def compute_hash(content):
    return hashlib.md5(content.encode('utf-8')).hexdigest()

# Function to send a message via Telegram
def send_telegram_message(chat_id, message):
    bot = telegram.Bot(token=bot_token)
    bot.send_message(chat_id=chat_id, text=message)

# Command handler for '/check' command
def check(update, context):
    session = start_session(login_url, credentials)
    content = get_page_content(session, target_url)
    extracted_content = extract_content(content)
    send_telegram_message(update.effective_chat.id, f'Content:\n{extracted_content}')

# Function to start the bot
def start_bot():
    updater = Updater(bot_token, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("check", check))

    updater.start_polling()
    updater.idle()

# Flask app for handling Telegram webhook
app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == "POST":
        update = telegram.Update.de_json(request.get_json(force=True), updater.bot)
        dp.process_update(update)
    return 'ok'

# Periodic tracking function
def track_page():
    session = start_session(login_url, credentials)
    current_content = get_page_content(session, target_url)
    current_hash = compute_hash(current_content)
    
    while True:
        time.sleep(300)  # Check every 5 minutes
        new_content = get_page_content(session, target_url)
        new_hash = compute_hash(new_content)
        
        if new_hash != current_hash:
            extracted_content = extract_content(new_content)
            send_telegram_message(chat_id, f'The webpage has been updated!\n\nContent:\n{extracted_content}')
            current_hash = new_hash

# Start the bot and tracking in separate threads
if __name__ == '__main__':
    threading.Thread(target=start_bot).start()
    threading.Thread(target=track_page).start()
