import os, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import telebot
TOKEN=os.getenv('BOT_TOKEN','').strip()
if not TOKEN: raise RuntimeError('BOT_TOKEN is required')
bot=telebot.TeleBot(TOKEN)
@bot.message_handler(commands=['start','menu'])
def start(message):
 bot.send_message(message.chat.id,'⭐ Casik Stars Bot запущен!')
class Health(BaseHTTPRequestHandler):
 def do_GET(self):
  self.send_response(200); self.end_headers(); self.wfile.write(b'Casik Stars Bot is running')
 def log_message(self,*args): pass
def main():
 threading.Thread(target=lambda:HTTPServer(('0.0.0.0',int(os.getenv('PORT','10000'))),Health).serve_forever(),daemon=True).start()
 bot.infinity_polling(skip_pending=True,timeout=30,long_polling_timeout=30)
if __name__=='__main__': main()
