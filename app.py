import os, re, sqlite3
from io import BytesIO
from flask import Flask, request, jsonify
import requests

app=Flask(__name__)
BOT_TOKEN=os.getenv('BOT_TOKEN','').strip()
ZENTO_API_BASE=os.getenv('ZENTO_API_BASE','https://zento.up.railway.app/api/bot').rstrip('/')
ADMIN_ID=os.getenv('ADMIN_ID','').strip()
DB_PATH=os.getenv('DB_PATH','bot.db')
OPENROUTER_API_KEY=os.getenv('OPENROUTER_API_KEY','').strip()
OPENROUTER_MODEL=os.getenv('OPENROUTER_MODEL','openai/gpt-oss-20b').strip()
HF_TOKEN=os.getenv('HF_TOKEN','').strip()
HF_IMAGE_MODEL=os.getenv('HF_IMAGE_MODEL','black-forest-labs/FLUX.1-schnell').strip()
HF_IMAGE_PROVIDER=os.getenv('HF_IMAGE_PROVIDER','auto').strip()
AI_SYSTEM_PROMPT=os.getenv('AI_SYSTEM_PROMPT','You are Zyro, a fast, helpful assistant. Answer in the same language as the user. Be concise unless detail is requested.').strip()

def db():
    c=sqlite3.connect(DB_PATH); c.row_factory=sqlite3.Row; return c

def init_db():
    c=db()
    c.execute('CREATE TABLE IF NOT EXISTS history(user_id TEXT NOT NULL,role TEXT NOT NULL,content TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP)')
    c.commit(); c.close()

def api_call(method,payload=None,timeout=15):
    if not BOT_TOKEN:return False,None
    try:
        r=requests.post(f'{ZENTO_API_BASE}/{BOT_TOKEN}/{method}',json=payload or {},timeout=timeout)
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
        r=requests.post(url,data=form,files=files,timeout=60)
        return r.ok
    except requests.RequestException:return False

def btn(text,data):return {'text':text,'callback_data':data}
def menu(rows):return {'inline_keyboard':rows}

def home(cid):
    send_message(cid,'✨ Zyro\n\nسریع، حرفه‌ای و ساده.\n\n💬 گفتگو با Zyro\n🖼️ ساخت تصویر\n\nانتخاب کن 👇',menu([[btn('💬 چت','chat')],[btn('🖼️ ساخت تصویر','image')]]))

def get_history(uid):
    c=db(); rows=c.execute('SELECT role,content FROM history WHERE user_id=? ORDER BY rowid DESC LIMIT 10',(str(uid),)).fetchall(); c.close()
    return [{'role':x['role'],'content':x['content']} for x in reversed(rows)]

def save_history(uid,role,content):
    c=db(); c.execute('INSERT INTO history(user_id,role,content) VALUES(?,?,?)',(str(uid),role,str(content))); c.execute('DELETE FROM history WHERE user_id=? AND rowid NOT IN (SELECT rowid FROM history WHERE user_id=? ORDER BY rowid DESC LIMIT 10)',(str(uid),str(uid))); c.commit(); c.close()

def chat(prompt,uid):
    if not OPENROUTER_API_KEY:return None,'کلید گفتگو در Railway تنظیم نشده است.'
    headers={'Authorization':f'Bearer {OPENROUTER_API_KEY}','Content-Type':'application/json','X-Title':'Zyro'}
    payload={'model':OPENROUTER_MODEL,'messages':[{'role':'system','content':AI_SYSTEM_PROMPT}]+get_history(uid)+[{'role':'user','content':prompt}],'temperature':0.3,'max_completion_tokens':900}
    try:
        r=requests.post('https://openrouter.ai/api/v1/chat/completions',headers=headers,json=payload,timeout=45)
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
        client=InferenceClient(provider=HF_IMAGE_PROVIDER or 'auto',api_key=HF_TOKEN,timeout=60)
        pic=client.text_to_image(prompt,model=HF_IMAGE_MODEL)
        b=BytesIO(); pic.save(b,format='PNG'); return b.getvalue(),None
    except Exception as e:
        t=str(e).lower()
        if '402' in t or 'payment required' in t:return None,'سرویس ساخت تصویر برای این حساب اعتبار کافی ندارد.'
        if 'deprecated' in t or 'unsupported' in t:return None,'مدل تصویر دیگر در دسترس نیست؛ HF_IMAGE_MODEL را تغییر بده.'
        return None,'ساخت تصویر ناموفق بود.'

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

def handle_callback(data):
    q=parse_callback(data)
    if not q:return
    cid,uid,action,qid=q; answer_callback(qid)
    if action=='home':home(cid)
    elif action=='chat':send_message(cid,'💬 پیام خودت را بفرست.',menu([[btn('🏠 بازگشت','home')]]))
    elif action=='image':send_message(cid,'🖼️ توضیح تصویری که می‌خواهی را بفرست.',menu([[btn('🏠 بازگشت','home')]]))

def handle_message(data):
    x=parse_message(data)
    if not x or x['chat_id'] is None:return
    cid=x['chat_id']; uid=x['user_id']; text=x['text']; typ=x['chat_type']
    if text.lower().strip() in ('/start','/ai','ai','zyro'):
        home(cid);return
    # In groups/channels Zyro answers when explicitly called by name.
    if typ in ('group','supergroup','channel') and is_mention(text):
        prompt=strip_mention(text)
        if prompt:handle_text(cid,uid,prompt)
        return
    # In private chats, ordinary text is a chat request.
    if typ not in ('group','supergroup','channel') and text and not text.startswith('/'):
        handle_text(cid,uid,text)

@app.get('/')
def root():return 'Zyro is running.'
@app.get('/health')
def health():return jsonify(ok=True,zyro=True,chat_model=OPENROUTER_MODEL,image_model=HF_IMAGE_MODEL)
@app.post('/webhook')
def webhook():
    data=request.get_json(silent=True) or {}
    handle_callback(data);handle_message(data)
    return jsonify(ok=True)

init_db()
if __name__=='__main__':app.run(host='0.0.0.0',port=int(os.getenv('PORT','8080')))
