import os, re, sqlite3, csv, tempfile, time
from io import BytesIO, StringIO
from flask import Flask, request, jsonify
import requests

app=Flask(__name__)
HTTP=requests.Session()
BOT_TOKEN=os.getenv('BOT_TOKEN','').strip()
ZENTO_API_BASE=os.getenv('ZENTO_API_BASE','https://zento.up.railway.app/api/bot').rstrip('/')
ADMIN_ID=os.getenv('ADMIN_ID','').strip()
DB_PATH=os.getenv('DB_PATH','bot.db')
OPENROUTER_API_KEY=os.getenv('OPENROUTER_API_KEY','').strip()
OPENROUTER_MODEL=os.getenv('OPENROUTER_MODEL','openai/gpt-oss-20b').strip()
OPENROUTER_TIMEOUT=int(os.getenv('AI_TIMEOUT','35'))
HF_TOKEN=os.getenv('HF_TOKEN','').strip()
HF_IMAGE_MODEL=os.getenv('HF_IMAGE_MODEL','black-forest-labs/FLUX.1-schnell').strip()
HF_IMAGE_PROVIDER=os.getenv('HF_IMAGE_PROVIDER','auto').strip()
AI_SYSTEM_PROMPT=os.getenv('AI_SYSTEM_PROMPT','You are Zyro, a fast, helpful assistant. Answer in the same language as the user. Be concise unless detail is requested.').strip()

def db():
    c=sqlite3.connect(DB_PATH); c.row_factory=sqlite3.Row; return c

def init_db():
    c=db()
    c.execute('CREATE TABLE IF NOT EXISTS history(user_id TEXT NOT NULL,role TEXT NOT NULL,content TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP)')
    c.execute("CREATE TABLE IF NOT EXISTS sessions(user_id TEXT PRIMARY KEY,mode TEXT DEFAULT 'chat')")
    c.commit(); c.close()

def set_mode(uid,mode):
    c=db(); c.execute("INSERT INTO sessions(user_id,mode) VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET mode=excluded.mode",(str(uid),mode)); c.commit(); c.close()

def get_mode(uid):
    c=db(); r=c.execute("SELECT mode FROM sessions WHERE user_id=?",(str(uid),)).fetchone(); c.close(); return r["mode"] if r else "chat"

def clear_history(uid):
    c=db(); c.execute("DELETE FROM history WHERE user_id=?",(str(uid),)); c.commit(); c.close()

def api_call(method,payload=None,timeout=10):
    if not BOT_TOKEN:return False,None
    try:
        r=HTTP.post(f'{ZENTO_API_BASE}/{BOT_TOKEN}/{method}',json=payload or {},timeout=timeout)
        try:d=r.json()
        except Exception:d=None
        return r.ok,d
    except requests.RequestException:return False,None

def send_message(cid,text,reply_markup=None):
    p={'chat_id':str(cid),'text':str(text)}
    if reply_markup:p['reply_markup']=reply_markup
    return api_call('sendMessage',p)[0]

def answer_callback(qid):
    if not qid:return
    api_call('answerCallbackQuery',{'callback_query_id':qid})

def send_photo(cid,data,caption=''):
    try:
        url=f'{ZENTO_API_BASE}/{BOT_TOKEN}/sendPhoto'
        files={'photo':('zyro.png',data,'image/png')}; form={'chat_id':str(cid)}
        if caption:form['caption']=caption
        r=HTTP.post(url,data=form,files=files,timeout=OPENROUTER_TIMEOUT)
        return r.ok
    except requests.RequestException:return False

def btn(text,data):return {'text':text,'callback_data':data}
def menu(rows):return {'inline_keyboard':rows}

def home(cid):
    text=('✨ Zyro\n\nدستیار هوشمند سریع و حرفه‌ای.\n\n💬 گفت‌وگو\n🖼️ تولید تصویر\n📎 ساخت فایل\n🧹 پاک کردن گفتگو\nℹ️ راهنما')
    send_message(cid,text,menu([[btn('💬 گفت‌وگو','chat'),btn('🖼️ تولید تصویر','image')],[btn('📎 ساخت فایل','file'),btn('🧹 پاک کردن','clear')],[btn('ℹ️ راهنما','help')]]))

def get_history(uid):
    c=db(); rows=c.execute('SELECT role,content FROM history WHERE user_id=? ORDER BY rowid DESC LIMIT 8',(str(uid),)).fetchall(); c.close()
    return [{'role':x['role'],'content':x['content']} for x in reversed(rows)]

def save_history(uid,role,content):
    c=db(); c.execute('INSERT INTO history(user_id,role,content) VALUES(?,?,?)',(str(uid),role,str(content))); c.execute('DELETE FROM history WHERE user_id=? AND rowid NOT IN (SELECT rowid FROM history WHERE user_id=? ORDER BY rowid DESC LIMIT 8)',(str(uid),str(uid))); c.commit(); c.close()

def chat(prompt,uid):
    if not OPENROUTER_API_KEY:return None,'کلید گفتگو در Railway تنظیم نشده است.'
    headers={'Authorization':f'Bearer {OPENROUTER_API_KEY}','Content-Type':'application/json','X-Title':'Zyro'}
    payload={'model':OPENROUTER_MODEL,'messages':[{'role':'system','content':AI_SYSTEM_PROMPT}]+get_history(uid)+[{'role':'user','content':prompt}],'temperature':0.3,'max_completion_tokens':700}
    try:
        r=HTTP.post('https://openrouter.ai/api/v1/chat/completions',headers=headers,json=payload,timeout=OPENROUTER_TIMEOUT)
        if not r.ok:
            return None,('مدل گفتگو در دسترس نیست. OPENROUTER_MODEL باید openai/gpt-oss-20b باشد.' if r.status_code==404 else 'پاسخ‌گویی موقتاً در دسترس نیست.')
        data=r.json(); answer=((data.get('choices') or [{}])[0].get('message') or {}).get('content')
        if not answer:return None,'پاسخ خالی دریافت شد.'
        answer=str(answer).strip(); save_history(uid,'user',prompt); save_history(uid,'assistant',answer); return answer,None
    except requests.RequestException:return None,'ارتباط با سرویس گفتگو برقرار نشد.'

def image(prompt):
    if not HF_TOKEN:return None,'کلید ساخت تصویر در Railway تنظیم نشده است.'
    try:
        from huggingface_hub import InferenceClient
        # These are current text-to-image models exposed through HF Inference Providers.
        models=[x.strip() for x in os.getenv(
            'HF_IMAGE_MODELS',
            'black-forest-labs/FLUX.1-dev,Qwen/Qwen-Image,black-forest-labs/FLUX.1-schnell'
        ).split(',') if x.strip()]
        provider=os.getenv('HF_IMAGE_PROVIDER','auto').strip() or 'auto'
        last=''
        for model in models:
            try:
                client=InferenceClient(provider=provider,api_key=HF_TOKEN,timeout=90)
                pic=client.text_to_image(prompt,model=model)
                b=BytesIO(); pic.save(b,format='PNG'); return b.getvalue(),None
            except Exception as e:
                last=f'{model}: {e}'
        low=last.lower()
        if '402' in low or 'payment required' in low or 'credit' in low:
            return None,'اعتبار Inference Providers برای ساخت تصویر کافی نیست. در Hugging Face بخش Billing/Inference را بررسی کن.'
        if '401' in low or '403' in low:
            return None,'HF_TOKEN دسترسی Inference لازم را ندارد.'
        if 'provider' in low and ('not supported' in low or 'no provider' in low):
            return None,'برای مدل انتخابی Provider فعال پیدا نشد. HF_IMAGE_PROVIDER را روی auto بگذار.'
        return None,'سرویس تصویر پاسخ نداد. در /health جزئیات مدل‌ها را بررسی کن.'
    except ImportError:return None,'کتابخانه huggingface_hub نصب نشده است.'
    except Exception as e:return None,f'تولید تصویر ناموفق بود: {str(e)[:180]}'

def send_document(cid,data,filename='zyro.txt',caption=''):
    try:
        url=f'{ZENTO_API_BASE}/{BOT_TOKEN}/sendDocument'
        files={'document':(filename,data,'application/octet-stream')}
        form={'chat_id':str(cid)}
        if caption: form['caption']=caption
        r=HTTP.post(url,data=form,files=files,timeout=45)
        return r.ok
    except requests.RequestException:return False

def make_file(prompt, answer):
    """Create a useful lightweight document from the AI answer without external storage."""
    low=prompt.lower()
    if any(x in low for x in ('csv','اکسل','excel')):
        out=StringIO(); w=csv.writer(out); w.writerow(['Zyro']);
        for line in answer.splitlines():
            w.writerow([line])
        return out.getvalue().encode('utf-8-sig'),'zyro.csv'
    if any(x in low for x in ('markdown','مارک‌داون','مارک داون','.md')):
        return answer.encode('utf-8'),'zyro.md'
    return answer.encode('utf-8'),'zyro.txt'

def is_mention(text):return bool(text and re.search(r'(^|[^a-z0-9_])@?zyro([^a-z0-9_]|$)',str(text),re.I))
def strip_mention(text):return re.sub(r'\\s+',' ',re.sub(r'(^|[^a-z0-9_])@?zyro(?=$|[^a-z0-9_])',' ',str(text),flags=re.I)).strip(' ,:؛،')

def parse_message(data):
    m=data.get('message') or data.get('msg') or data.get('channel_post')
    if not isinstance(m,dict):return None
    ch=m.get('chat') or {}; sender=m.get('from') or m.get('sender') or {}
    return {'chat_id':ch.get('id'),'chat_type':ch.get('type',''),'user_id':sender.get('id') or ch.get('id'),'text':(m.get('text') or '').strip(),'message_id':m.get('message_id') or m.get('id'),'message':m}

def parse_callback(data):
    q=data.get('callback_query') or data.get('callback')
    if not isinstance(q,dict):return None
    m=q.get('message') or q.get('msg') or {}; ch=m.get('chat') or {}; s=q.get('from') or q.get('sender') or {}
    return ch.get('id'),s.get('id') or ch.get('id'),str(q.get('data') or q.get('callback_data') or ''),q.get('id') or q.get('callback_query_id')

def handle_text(cid,uid,text):
    if not text:return
    answer,err=chat(text,uid)
    if err:send_message(cid,'❌ '+err,menu([[btn('🏠 Zyro','home')]]))
    else:send_message(cid,'✨ Zyro\n\n'+answer,menu([[btn('💬 ادامه','chat'),btn('🖼️ تصویر','image')]]))

def handle_image(cid,prompt):
    if not prompt:return
    data,err=image(prompt)
    if err:send_message(cid,'❌ '+err,menu([[btn('🏠 Zyro','home')]]));return
    if not send_photo(cid,data,'✨ Zyro'):
        send_message(cid,'❌ تصویر ساخته شد اما ارسال آن ناموفق بود.')

def handle_file(cid,uid,prompt):
    answer,err=chat(prompt,uid)
    if err:
        send_message(cid,'❌ '+err,menu([[btn('🏠 خانه','home')]])); return
    data,name=make_file(prompt,answer)
    if not send_document(cid,data,name,'📎 فایل ساخته‌شده توسط Zyro'):
        send_message(cid,'❌ فایل ساخته شد اما ارسال آن ناموفق بود.')
    else:
        set_mode(uid,'file')

def handle_callback(data):
    q=parse_callback(data)
    if not q:return
    cid,uid,action,qid=q; answer_callback(qid)
    if action=='home': set_mode(uid,'chat'); home(cid)
    elif action=='chat': set_mode(uid,'chat'); send_message(cid,'💬 حالت گفت‌وگو فعال شد.\nپیامت را بفرست.',menu([[btn('🖼️ تصویر','image'),btn('🧹 پاک کردن','clear')],[btn('🏠 خانه','home')]]))
    elif action=='image': set_mode(uid,'image'); send_message(cid,'🖼️ حالت تولید تصویر فعال شد.\nتوضیح تصویر را بفرست.',menu([[btn('💬 چت','chat'),btn('🏠 خانه','home')]]))
    elif action=='clear': clear_history(uid); set_mode(uid,'chat'); send_message(cid,'🧹 حافظه گفت‌وگو پاک شد.',menu([[btn('💬 چت','chat'),btn('🏠 خانه','home')]]))
    elif action=='help':
        send_message(cid,'ℹ️ راهنمای Zyro\n\n💬 برای گفتگو پیام بفرست.\n🖼️ برای تصویر، «تولید تصویر» را انتخاب کن و توضیحت را بفرست.\n👥 در گروه یا کانال، Zyro یا @Zyro را صدا بزن.\n📎 برای ساخت فایل، حالت فایل را انتخاب کن.\n🧹 برای شروع یک گفت‌وگوی تازه، حافظه را پاک کن.',menu([[btn('🏠 خانه','home')]]))

def handle_message(data):
    x=parse_message(data)
    if not x or x['chat_id'] is None:return
    cid=x['chat_id']; uid=x['user_id']; text=x['text']; typ=x['chat_type']
    cmd=text.lower().strip()
    if cmd in ('/start','/ai','ai','zyro'):
        set_mode(uid,'chat'); home(cid);return
    if cmd in ('/clear','/new'):
        clear_history(uid); set_mode(uid,'chat'); send_message(cid,'🧹 گفت‌وگوی تازه آماده است.',menu([[btn('💬 شروع','chat'),btn('🏠 خانه','home')]])); return
    if cmd in ('/help','راهنما'):
        send_message(cid,'ℹ️ راهنمای Zyro\n\n💬 گفت‌وگو: پیام خود را بفرست.\n🖼️ تصویر: از منوی اصلی تولید تصویر را انتخاب کن.\n👥 گروه/کانال: Zyro یا @Zyro را صدا بزن.\n📎 فایل: متن را به فایل تبدیل می‌کند.\n🧹 /clear برای گفت‌وگوی تازه.',menu([[btn('🏠 خانه','home')]])); return
    # In groups/channels Zyro answers when explicitly called by name.
    if typ in ('group','supergroup','channel') and is_mention(text):
        prompt=strip_mention(text)
        if prompt:handle_text(cid,uid,prompt)
        return
    # In private chats, ordinary text is a chat request.
    if typ not in ('group','supergroup','channel') and text and not text.startswith('/'):
        mode=get_mode(uid)
        if mode=='image': handle_image(cid,text)
        elif mode=='file': handle_file(cid,uid,text)
        else: handle_text(cid,uid,text)

@app.get('/')
def root():return 'Zyro is running.'
@app.get('/health')
def health():return jsonify(ok=True,zyro=True,chat_model=OPENROUTER_MODEL,image_models=os.getenv('HF_IMAGE_MODELS','black-forest-labs/FLUX.1-schnell,Qwen/Qwen-Image').split(','),image_provider=os.getenv('HF_IMAGE_PROVIDER','auto'))
@app.post('/webhook')
def webhook():
    data=request.get_json(silent=True) or {}
    handle_callback(data);handle_message(data)
    return jsonify(ok=True)

init_db()
if __name__=='__main__':app.run(host='0.0.0.0',port=int(os.getenv('PORT','8080')))
