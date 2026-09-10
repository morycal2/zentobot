import os, sqlite3
from datetime import datetime, timezone
from flask import Flask, request, jsonify
import requests
app=Flask(__name__)
BOT_TOKEN=os.getenv('BOT_TOKEN','').strip()
ZENTO_API_BASE=os.getenv('ZENTO_API_BASE','https://zento.up.railway.app/api/bot').rstrip('/')
ADMIN_ID=os.getenv('ADMIN_ID','').strip(); DB_PATH=os.getenv('DB_PATH','bot.db')
ENABLE_KEYBOARD=os.getenv('ENABLE_KEYBOARD','false').lower()=='true'
def db():
 c=sqlite3.connect(DB_PATH); c.row_factory=sqlite3.Row; return c
def init_db():
 c=db(); c.execute('''CREATE TABLE IF NOT EXISTS users(user_id TEXT PRIMARY KEY,username TEXT DEFAULT '',first_name TEXT DEFAULT '',points INTEGER DEFAULT 0,last_daily TEXT DEFAULT '')'''); c.commit(); c.close()
def upsert_user(uid,username='',first_name=''):
 c=db(); c.execute('''INSERT INTO users(user_id,username,first_name) VALUES(?,?,?) ON CONFLICT(user_id) DO UPDATE SET username=excluded.username,first_name=excluded.first_name''',(str(uid),username or '',first_name or '')); c.commit(); c.close()
def get_user(uid):
 c=db(); r=c.execute('SELECT * FROM users WHERE user_id=?',(str(uid),)).fetchone(); c.close(); return r
def add_points(uid,n):
 c=db(); c.execute('UPDATE users SET points=points+? WHERE user_id=?',(n,str(uid))); c.commit(); c.close()
def send_message(chat_id,text):
 if not BOT_TOKEN:return False
 p={'chat_id':chat_id,'text':text}
 if ENABLE_KEYBOARD:p['reply_markup']={'keyboard':[[{'text':'👤 پروفایل من'},{'text':'⭐ امتیازات'}],[{'text':'🎁 جایزه روزانه'},{'text':'💬 پشتیبانی'}],[{'text':'📚 راهنما'}]],'resize_keyboard':True}
 try:return requests.post(f'{ZENTO_API_BASE}/{BOT_TOKEN}/sendMessage',json=p,timeout=15).ok
 except requests.RequestException:return False
def parse_update(data):
 m=data.get('message') or data.get('msg') or data.get('update')
 if not isinstance(m,dict):return (None,)*5
 ch=m.get('chat') or {}; s=m.get('from') or m.get('sender') or {}; text=m.get('text') or ''
 return ch.get('id'),s.get('id') or ch.get('id'),s.get('username',''),s.get('first_name') or s.get('name') or '',text.strip()
def today():return datetime.now(timezone.utc).date().isoformat()
def handle_message(cid,uid,username,first_name,text):
 if cid is None or uid is None:return
 upsert_user(uid,username,first_name); cmd=text.lower().strip()
 if cmd in ('/start','start','منو','menu'):
  add_points(uid,1); send_message(cid,'سلام 👋\n\nبه ربات خوش اومدی!\n\n👤 /profile — پروفایل من\n⭐ /points — امتیازات\n🎁 /daily — جایزه روزانه\n💬 /support — پشتیبانی\n📚 /help — راهنما')
 elif cmd in ('/profile','👤 پروفایل من','پروفایل','profile'):
  u=get_user(uid); send_message(cid,f"👤 پروفایل شما\n\nنام: {u['first_name'] or 'بدون نام'}\nشناسه: {u['user_id']}\nنام کاربری: @{u['username'] if u['username'] else 'ندارد'}\n⭐ امتیاز: {u['points']}")
 elif cmd in ('/points','⭐ امتیازات','امتیازات','points'):
  send_message(cid,f"⭐ امتیاز فعلی شما: {get_user(uid)['points']}")
 elif cmd in ('/daily','🎁 جایزه روزانه','جایزه روزانه','daily'):
  u=get_user(uid)
  if u['last_daily']==today():send_message(cid,'⏳ جایزه امروزت رو قبلاً گرفتی.\nفردا دوباره برگرد 🎁')
  else:
   c=db(); c.execute('UPDATE users SET points=points+5,last_daily=? WHERE user_id=?',(today(),str(uid))); c.commit(); c.close(); send_message(cid,'🎁 جایزه روزانه دریافت شد!\n\n+5 امتیاز ⭐')
 elif cmd in ('/help','📚 راهنما','راهنما','help'):
  send_message(cid,'📚 راهنمای ربات\n\n/start — شروع\n/profile — پروفایل\n/points — امتیاز\n/daily — جایزه روزانه\n/support — پشتیبانی\n/help — راهنما')
 elif cmd in ('/support','💬 پشتیبانی','پشتیبانی','support'):
  send_message(cid,'💬 پشتیبانی\n\nپیامت رو همین‌جا بفرست تا ثبت بشه.\nدر نسخه بعدی می‌تونیم سیستم تیکت و پنل پشتیبانی کامل اضافه کنیم.')
 elif cmd in ('/stats','stats','آمار'):
  if ADMIN_ID and str(uid)!=ADMIN_ID: send_message(cid,'⛔ این دستور فقط برای مدیر ربات است.'); return
  c=db(); count=c.execute('SELECT COUNT(*) FROM users').fetchone()[0]; total=c.execute('SELECT COALESCE(SUM(points),0) FROM users').fetchone()[0]; c.close(); send_message(cid,f'📊 آمار ربات\n\n👥 کاربران: {count}\n⭐ مجموع امتیازها: {total}\n🚀 نسخه: 2')
 else:send_message(cid,'❓ دستور رو متوجه نشدم.\nبرای راهنما /help رو بفرست.')
@app.get('/')
def home():return 'Zento Bot v2 is running.'
@app.get('/health')
def health():
 c=db(); n=c.execute('SELECT COUNT(*) FROM users').fetchone()[0]; c.close(); return jsonify({'ok':True,'version':2,'users':n})
@app.post('/webhook')
def webhook():
 cid,uid,un,fn,text=parse_update(request.get_json(silent=True) or {}); handle_message(cid,uid,un,fn,text); return jsonify({'ok':True})
init_db()
if __name__=='__main__':app.run(host='0.0.0.0',port=int(os.getenv('PORT','8080')))
