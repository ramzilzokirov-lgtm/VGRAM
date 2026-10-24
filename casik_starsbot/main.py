import os
import telebot
TOKEN=os.getenv('BOT_TOKEN','').strip()
if not TOKEN: raise RuntimeError('BOT_TOKEN is required')
bot=telebot.TeleBot(TOKEN)
@bot.message_handler(commands=['start','menu'])
def start(message):
 bot.send_message(message.chat.id,'⭐ Casik Stars Bot запущен!')
bot.infinity_polling(skip_pending=True)
