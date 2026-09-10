import os
import sqlite3
from datetime import datetime, timezone
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)
BOT_TOKEN = os.getenv('BOT_TOKEN','').strip()
ZENTO_API_BASE = os.getenv('ZENTO_API_BASE','https://zento.up.railway.app/api/bot').rstrip('/')
ADMIN_ID = os.getenv('ADMIN_ID','').strip()
DB_PATH = os.getenv('DB_PATH','bot.db')
BAD_WORDS = [x.strip().lower() for x in os.getenv('BAD_WORDS','چرت').split('|') if x.strip()]


def db():
    c=sqlite3.connect(DB_PATH); c.row_factory=sqlite3.Row; return c

def init_db():
    c=db()
    c.execute('CREATE TABLE IF NOT EXISTS users(user_id TEXT PRIMARY KEY,username TEXT DEFAULT "",first_name TEXT DEFAULT "",points INTEGER DEFAULT 0,last_daily TEXT DEFAULT "")')
    c.execute('CREATE TABLE IF NOT EXISTS warnings(chat_id TEXT NOT NULL,user_id TEXT NOT NULL,count INTEGER DEFAULT 0,PRIMARY KEY(chat_id,user_id))')
    c.execute('CREATE TABLE IF NOT EXISTS chats(chat_id TEXT PRIMARY KEY,title TEXT DEFAULT "",chat_type TEXT DEFAULT "",moderation INTEGER DEFAULT 1)')
    c.execute('CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT DEFAULT "")')
    defaults={'moderation':'1','auto_ban':'1','greetings':'1','max_warnings':'1'}
    for k,v in defaults.items(): c.execute('INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)',(k,v))
    c.commit(); c.close()

def setting(k, default=''):
    c=db(); r=c.execute('SELECT value FROM settings WHERE key=?',(k,)).fetchone(); c.close(); return r['value'] if r else default

def set_setting(k,v):
    c=db(); c.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(k,str(v))); c.commit(); c.close()

def upsert_user(uid,username='',first_name=''):
    if uid is None:return
    c=db(); c.execute('INSERT INTO users(user_id,username,first_name) VALUES(?,?,?) ON CONFLICT(user_id) DO UPDATE SET username=excluded.username,first_name=excluded.first_name',(str(uid),username or '',first_name or '')); c.commit(); c.close()

def get_user(uid):
    c=db(); r=c.execute('SELECT * FROM users WHERE user_id=?',(str(uid),)).fetchone(); c.close(); return r

def add_points(uid,n):
    c=db(); c.execute('UPDATE users SET points=points+? WHERE user_id=?',(n,str(uid))); c.commit(); c.close()

def add_warning(chat_id,uid):
    c=db(); c.execute('INSERT INTO warnings(chat_id,user_id,count) VALUES(?,?,1) ON CONFLICT(chat_id,user_id) DO UPDATE SET count=count+1',(str(chat_id),str(uid))); r=c.execute('SELECT count FROM warnings WHERE chat_id=? AND user_id=?',(str(chat_id),str(uid))).fetchone(); c.commit(); c.close(); return r['count']

def reset_warning(chat_id,uid):
    c=db(); c.execute('DELETE FROM warnings WHERE chat_id=? AND user_id=?',(str(chat_id),str(uid))); c.commit(); c.close()

def save_chat(cid,title,ctype):
    if cid is None:return
    c=db(); c.execute('INSERT INTO chats(chat_id,title,chat_type) VALUES(?,?,?) ON CONFLICT(chat_id) DO UPDATE SET title=excluded.title,chat_type=excluded.chat_type',(str(cid),title or '',ctype or '')); c.commit(); c.close()

def today(): return datetime.now(timezone.utc).date().isoformat()

def api_call(method,payload=None):
    if not BOT_TOKEN:return False,None
    try:
        r=requests.post(f'{ZENTO_API_BASE}/{BOT_TOKEN}/{method}',json=payload or {},timeout=15)
        try:data=r.json()
        except ValueError:data=None
        return r.ok,data
    except requests.RequestException:return False,None

def send_message(chat_id,text,reply_markup=None):
    p={'chat_id':chat_id,'text':text}
    if reply_markup is not None:p['reply_markup']=reply_markup
    return api_call('sendMessage',p)[0]

def delete_message(chat_id,message_id): return bool(message_id) and api_call('deleteMessage',{'chat_id':chat_id,'message_id':message_id})[0]
def ban_chat_member(chat_id,user_id): return api_call('banChatMember',{'chat_id':chat_id,'user_id':user_id})[0]
def unban_chat_member(chat_id,user_id): return api_call('unbanChatMember',{'chat_id':chat_id,'user_id':user_id})[0]
def answer_callback(callback_id): return bool(callback_id) and api_call('answerCallbackQuery',{'callback_query_id':callback_id})[0]

# ---------- glass UI ----------
def btn(text,data): return {'text':text,'callback_data':data}
def menu(rows): return {'inline_keyboard':rows}

def main_menu(): return menu([[btn('👤 پروفایل','profile'),btn('⭐ امتیازات','points')],[btn('🎁 جایزه روزانه','daily'),btn('💬 پشتیبانی','support')],[btn('📚 راهنما','help'),btn('ℹ️ درباره','about')],[btn('🔄 بروزرسانی','menu')]])
def back(): return menu([[btn('🏠 منوی اصلی','menu')]])
def admin_menu(): return menu([[btn('📊 داشبورد','adm:dashboard'),btn('🛡️ مدیریت','adm:moderation')],[btn('🚫 کلمات ممنوع','adm:words'),btn('👥 گروه‌ها','adm:chats')],[btn('📢 ارسال همگانی','adm:broadcast'),btn('⚙️ تنظیمات','adm:settings')],[btn('📋 راهنمای مدیر','adm:help'),btn('🏠 خروج','menu')]])
def moderation_menu(): return menu([[btn('🛡️ روشن/خاموش','adm:togglemod'),btn('🚫 بن خودکار','adm:toggleban')],[btn('⚠️ ریست اخطار','adm:resetwarn')],[btn('🔙 پنل مدیر','admin')]])
def settings_menu(): return menu([[btn('👋 پاسخ سلام','adm:togglegreet')],[btn('🛡️ وضعیت سیستم','adm:status')],[btn('🔙 پنل مدیر','admin')]])
def chats_menu():
    c=db(); rows=c.execute('SELECT chat_id,title,chat_type,moderation FROM chats ORDER BY rowid DESC LIMIT 12').fetchall(); c.close()
    keys=[]
    for r in rows:
        title=(r['title'] or r['chat_id'])[:24]
        keys.append([btn(('🟢 ' if r['moderation'] else '🔴 ')+title,f'adm:chat:{r["chat_id"]}')])
    keys += [[btn('🔙 پنل مدیر','admin')]]
    return menu(keys)

# ---------- normal screens ----------
def show_home(cid,uid):
    u=get_user(uid); name=(u['first_name'] if u else '') or 'دوست من'
    send_message(cid,f'✨ سلام {name}!\n\nبه ربات زنتو خوش اومدی 🌟\n\nاز منوی زیر امکانات ربات رو مدیریت کن 👇',main_menu())
def show_profile(cid,uid):
    u=get_user(uid); send_message(cid,f'👤 پروفایل کاربری\n\n🪪 نام: {(u["first_name"] if u else "بدون نام")}\n🆔 شناسه: {uid}\n🔗 نام کاربری: @{u["username"] if u and u["username"] else "ندارد"}\n⭐ امتیاز: {u["points"] if u else 0}',menu([[btn('⭐ امتیازات','points'),btn('🎁 جایزه','daily')],[btn('🏠 خانه','menu')]]))
def show_points(cid,uid): send_message(cid,f'⭐ امتیازات شما\n\nموجودی: {(get_user(uid)["points"] if get_user(uid) else 0)} ⭐',back())
def show_daily(cid,uid):
    u=get_user(uid)
    if u and u['last_daily']==today(): text='⏳ امروز جایزه‌ات رو گرفتی. فردا برگرد 🎁'
    else:
        c=db(); c.execute('UPDATE users SET points=points+5,last_daily=? WHERE user_id=?',(today(),str(uid))); c.commit(); c.close(); text='🎉 جایزه روزانه دریافت شد!\n\n+5 ⭐'
    send_message(cid,text,back())
def show_help(cid): send_message(cid,'📚 راهنما\n\n👋 ربات به سلام و احوالپرسی پاسخ می‌دهد.\n🛡️ در گروه‌ها می‌تواند پیام‌های ممنوع را مدیریت کند.\n👑 مدیر اصلی از /admin وارد پنل شیشه‌ای می‌شود.\n\nبرای مدیریت گروه، ربات باید دسترسی‌های لازم را داشته باشد.',back())
def show_support(cid): send_message(cid,'💬 پشتیبانی\n\nپیامت رو همین‌جا ارسال کن.',back())
def show_about(cid): send_message(cid,'ℹ️ Zento Bot\n\n⚡ Flask + SQLite\n🎛️ پنل شیشه‌ای حرفه‌ای\n🛡️ مدیریت گروه\n📢 ابزارهای مدیر',back())

# ---------- admin screens ----------
def admin_dashboard(cid):
    c=db(); users=c.execute('SELECT COUNT(*) n FROM users').fetchone()['n']; chats=c.execute('SELECT COUNT(*) n FROM chats').fetchone()['n']; warns=c.execute('SELECT COALESCE(SUM(count),0) n FROM warnings').fetchone()['n']; points=c.execute('SELECT COALESCE(SUM(points),0) n FROM users').fetchone()['n']; c.close()
    text=f'👑 داشبورد مدیریت\n\n👥 کاربران: {users}\n👥 گروه/کانال ثبت‌شده: {chats}\n⚠️ اخطارهای ثبت‌شده: {warns}\n⭐ مجموع امتیازها: {points}\n\n🟢 سیستم آماده است.'
    send_message(cid,text,admin_menu())
def admin_moderation(cid):
    send_message(cid,f'🛡️ مدیریت محتوا\n\nوضعیت فیلتر: {"🟢 روشن" if setting("moderation","1")=="1" else "🔴 خاموش"}\nبن خودکار: {"🟢 روشن" if setting("auto_ban","1")=="1" else "🔴 خاموش"}\n\n⚠️ برای تغییرات روی دکمه‌ها بزن.',moderation_menu())
def admin_words(cid):
    words='\n'.join(f'• {w}' for w in BAD_WORDS) or 'لیست خالی است.'
    send_message(cid,f'🚫 کلمات/عبارت‌های ممنوع\n\n{words}\n\n➕ افزودن: /addword عبارت\n➖ حذف: /delword عبارت\n🧹 پاک‌کردن همه: /clearwords',menu([[btn('🔙 پنل مدیر','admin')]]))
def admin_chats(cid):
    send_message(cid,'👥 گروه‌ها و کانال‌های شناخته‌شده\n\nبا ارسال /start یا هر پیام در یک گروه، آن گروه در لیست ثبت می‌شود.\nروی نام هر مورد بزن تا وضعیت فیلتر آن را تغییر بدهی.',chats_menu())
def admin_settings(cid):
    send_message(cid,f'⚙️ تنظیمات\n\n👋 پاسخ سلام: {"🟢 روشن" if setting("greetings","1")=="1" else "🔴 خاموش"}\n🛡️ فیلتر: {"🟢 روشن" if setting("moderation","1")=="1" else "🔴 خاموش"}\n🚫 بن خودکار: {"🟢 روشن" if setting("auto_ban","1")=="1" else "🔴 خاموش"}',settings_menu())
def admin_help(cid):
    send_message(cid,'📋 راهنمای مدیر\n\n/admin — پنل مدیریت\n/addword متن — افزودن کلمه ممنوع\n/delword متن — حذف کلمه\n/clearwords — حذف همه کلمات\n/send CHAT_ID متن — ارسال پیام\n/ban CHAT_ID USER_ID — بن\n/unban CHAT_ID USER_ID — آن‌بن\n/resetwarn CHAT_ID USER_ID — پاک کردن اخطار\n/broadcast متن — ارسال به همه چت‌های ثبت‌شده\n\nبرای بن/حذف پیام، ربات باید ادمین و دارای دسترسی لازم باشد.',menu([[btn('🔙 پنل مدیر','admin')]]))

def admin_broadcast(cid,uid,text=None):
    if text and text.startswith('/broadcast '):
        message=text.split(' ',1)[1]
        c=db(); chats=c.execute('SELECT chat_id FROM chats').fetchall(); c.close(); ok=0
        for r in chats:
            if send_message(r['chat_id'],message): ok+=1
        send_message(cid,f'📢 ارسال همگانی انجام شد.\n\n✅ موفق: {ok}\n📦 کل مقصدها: {len(chats)}',admin_menu())
    else: send_message(cid,'📢 ارسال همگانی\n\nفرمت:\n/broadcast متن پیام\n\nپیام به تمام گروه‌ها/کانال‌های ثبت‌شده ارسال می‌شود.',admin_menu())

def admin_resetwarn(cid,text):
    parts=text.split()
    if len(parts)<3:return send_message(cid,'فرمت: /resetwarn CHAT_ID USER_ID',admin_menu())
    reset_warning(parts[1],parts[2]); send_message(cid,'✅ اخطارهای کاربر پاک شد.',admin_menu())

def is_owner(uid): return bool(ADMIN_ID) and str(uid)==str(ADMIN_ID)

def greeting_reply(text):
    t=' '.join((text or '').lower().split())
    if not t:return None
    if t in {'سلام','سلام!','سلام 👋','hello','hi','salam'} or t.startswith('سلام '): return 'سلام رفیق 👋❤️ خوبی؟'
    if 'خوبی' in t:return 'مرسی رفیق 😎 من خوبم، تو خوبی؟'
    if 'چه خبر' in t or 'چطوری' in t:return 'همه‌چی روبه‌راهه 😎🔥 تو چطوری؟'
    return None

def is_bad_message(text):
    t=' '.join((text or '').lower().split())
    return bool(t) and any(w in t for w in BAD_WORDS)

def moderate_message(chat_id,chat_type,uid,text,message_id):
    if chat_type not in {'group','supergroup','channel'} or not uid or setting('moderation','1')!='1' or not is_bad_message(text):return False
    if ADMIN_ID and str(uid)==str(ADMIN_ID):return False
    delete_message(chat_id,message_id); count=add_warning(chat_id,uid)
    if setting('auto_ban','1')=='1' and count>=int(setting('max_warnings','1') or 1):
        banned=ban_chat_member(chat_id,uid)
        if banned: send_message(chat_id,f'🛡️ کاربر {uid} به دلیل ارسال پیام نامناسب مسدود شد.\n⚠️ تخلف: {count}')
        else: send_message(chat_id,'⚠️ پیام حذف شد؛ برای بن خودکار ربات باید ادمین و دارای دسترسی مسدود کردن اعضا باشد.')
    else: send_message(chat_id,f'⚠️ پیام نامناسب حذف شد.\nاخطار کاربر: {count}')
    return True

def parse_message(data):
    m=data.get('message') or data.get('msg') or data.get('channel_post')
    if not isinstance(m,dict):return (None,)*9
    ch=m.get('chat') or {}; s=m.get('from') or m.get('sender') or {}
    return ch.get('id'),ch.get('type',''),s.get('id') or ch.get('id'),s.get('username',''),s.get('first_name') or s.get('name') or '',(m.get('text') or '').strip(),m.get('message_id') or m.get('id'),ch.get('title') or ch.get('name') or '',bool(m.get('channel_post'))

def parse_callback(data):
    q=data.get('callback_query') or data.get('callback')
    if not isinstance(q,dict):return (None,)*6
    m=q.get('message') or q.get('msg') or {}; ch=m.get('chat') or {}; s=q.get('from') or q.get('sender') or {}
    return ch.get('id'),s.get('id') or ch.get('id'),s.get('username',''),s.get('first_name') or s.get('name') or '',str(q.get('data') or q.get('callback_data') or '').strip(),q.get('id') or q.get('callback_query_id')

def admin_action(cid,uid,action):
    if not is_owner(uid):send_message(cid,'⛔ دسترسی فقط برای مدیر اصلی است.');return
    if action=='admin':admin_dashboard(cid)
    elif action=='adm:dashboard':admin_dashboard(cid)
    elif action=='adm:moderation':admin_moderation(cid)
    elif action=='adm:words':admin_words(cid)
    elif action=='adm:chats':admin_chats(cid)
    elif action=='adm:broadcast':admin_broadcast(cid,uid)
    elif action=='adm:settings':admin_settings(cid)
    elif action=='adm:help':admin_help(cid)
    elif action=='adm:togglemod':set_setting('moderation','0' if setting('moderation','1')=='1' else '1');admin_moderation(cid)
    elif action=='adm:toggleban':set_setting('auto_ban','0' if setting('auto_ban','1')=='1' else '1');admin_moderation(cid)
    elif action=='adm:togglegreet':set_setting('greetings','0' if setting('greetings','1')=='1' else '1');admin_settings(cid)
    elif action=='adm:status':admin_settings(cid)
    elif action=='adm:resetwarn':send_message(cid,'⚠️ برای ریست اخطار:\n/resetwarn CHAT_ID USER_ID',moderation_menu())
    elif action.startswith('adm:chat:'):
        target=action.split(':',2)[2]; c=db(); r=c.execute('SELECT moderation FROM chats WHERE chat_id=?',(target,)).fetchone(); new=0 if r and r['moderation'] else 1; c.execute('UPDATE chats SET moderation=? WHERE chat_id=?',(new,target)); c.commit(); c.close(); admin_chats(cid)

def add_word(cid,text):
    global BAD_WORDS
    if not is_owner(cid): return
    w=text.split(' ',1)[1].strip().lower() if ' ' in text else ''
    if w and w not in BAD_WORDS:BAD_WORDS.append(w); set_setting('bad_words','|'.join(BAD_WORDS))
    send_message(cid,'✅ عبارت اضافه شد.' if w else 'فرمت: /addword عبارت',admin_words(cid) if False else menu([[btn('🚫 لیست کلمات','adm:words'),btn('🔙 پنل','admin')]]))

def del_word(cid,text):
    global BAD_WORDS
    w=text.split(' ',1)[1].strip().lower() if ' ' in text else ''
    if w in BAD_WORDS:BAD_WORDS.remove(w);set_setting('bad_words','|'.join(BAD_WORDS));msg='✅ حذف شد.'
    else:msg='⚠️ چنین عبارتی در لیست نبود.'
    send_message(cid,msg,menu([[btn('🚫 لیست کلمات','adm:words'),btn('🔙 پنل','admin')]]))

def handle_message(cid,chat_type,uid,username,first_name,text,message_id,title):
    if cid is None:return
    if uid is not None:upsert_user(uid,username,first_name)
    save_chat(cid,title,chat_type)
    if uid is not None and moderate_message(cid,chat_type,uid,text,message_id):return
    cmd=(text or '').lower().strip()
    if is_owner(uid) and cmd=='/admin':admin_dashboard(cid);return
    if cmd.startswith('/addword '):add_word(uid,text);return
    if cmd.startswith('/delword '):del_word(uid,text);return
    if cmd=='/clearwords' and is_owner(uid):
        global BAD_WORDS; BAD_WORDS=[];set_setting('bad_words','');send_message(cid,'🧹 لیست کلمات پاک شد.',admin_menu());return
    if cmd.startswith('/broadcast '):
        admin_broadcast(cid,uid,text);return
    if cmd.startswith('/send '):
        if not is_owner(uid):send_message(cid,'⛔ فقط مدیر.');return
        p=text.split(maxsplit=2)
        if len(p)<3:send_message(cid,'فرمت: /send CHAT_ID متن',admin_menu())
        else:send_message(cid,'✅ ارسال شد.' if send_message(p[1],p[2]) else '❌ ارسال ناموفق.',admin_menu())
        return
    if cmd.startswith('/ban '):
        if is_owner(uid):
            p=text.split(); ok=len(p)>=3 and ban_chat_member(p[1],p[2]);send_message(cid,'✅ بن شد.' if ok else '❌ بن انجام نشد.',admin_menu())
        return
    if cmd.startswith('/unban '):
        if is_owner(uid):
            p=text.split(); ok=len(p)>=3 and unban_chat_member(p[1],p[2]);send_message(cid,'✅ آن‌بن شد.' if ok else '❌ آن‌بن انجام نشد.',admin_menu())
        return
    if cmd.startswith('/resetwarn '):
        if is_owner(uid):admin_resetwarn(cid,text)
        return
    if setting('greetings','1')=='1':
        g=greeting_reply(text)
        if g:send_message(cid,g);return
    if cmd in ('/start','start','منو','menu') and uid is not None:add_points(uid,1);show_home(cid,uid)
    elif cmd in ('/profile','پروفایل','profile') and uid is not None:show_profile(cid,uid)
    elif cmd in ('/points','امتیازات','points') and uid is not None:show_points(cid,uid)
    elif cmd in ('/daily','جایزه روزانه','daily') and uid is not None:show_daily(cid,uid)
    elif cmd in ('/help','راهنما','help'):show_help(cid)
    elif cmd in ('/support','پشتیبانی','support'):show_support(cid)
    elif cmd in ('/about','درباره','about'):show_about(cid)
    elif cmd in ('/stats','stats','آمار') and is_owner(uid):admin_dashboard(cid)
    elif chat_type not in {'group','supergroup','channel'}:send_message(cid,'❓ دستور نامشخصه. /start رو بفرست.',main_menu())

def handle_callback(data):
    cid,uid,un,fn,action,qid=parse_callback(data)
    if cid is None or not action:return
    if qid:answer_callback(qid)
    upsert_user(uid,un,fn)
    if action.startswith('adm:') or action=='admin':admin_action(cid,uid,action)
    elif action=='menu':show_home(cid,uid)
    elif action=='profile':show_profile(cid,uid)
    elif action=='points':show_points(cid,uid)
    elif action=='daily':show_daily(cid,uid)
    elif action=='help':show_help(cid)
    elif action=='support':show_support(cid)
    elif action=='about':show_about(cid)

@app.get('/')
def home():return 'Zento Bot v5 - Professional Admin Panel is running.'
@app.get('/health')
def health():
    c=db(); u=c.execute('SELECT COUNT(*) n FROM users').fetchone()['n'];ch=c.execute('SELECT COUNT(*) n FROM chats').fetchone()['n'];c.close();return jsonify(ok=True,version=5,users=u,chats=ch,admin_panel=True)
@app.post('/webhook')
def webhook():
    data=request.get_json(silent=True) or {}
    handle_callback(data)
    cid,ctype,uid,un,fn,text,mid,title,_=parse_message(data)
    if cid is not None:handle_message(cid,ctype,uid,un,fn,text,mid,title)
    return jsonify(ok=True)

init_db()
if __name__=='__main__':app.run(host='0.0.0.0',port=int(os.getenv('PORT','8080')))
