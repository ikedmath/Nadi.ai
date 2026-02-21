import os
import requests
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# 1. جلب السوارت من الإعدادات (آمن 100%)
GEMINI_KEY = os.getenv("GEMINI_KEY")
WHAPI_TOKEN = os.getenv("WHAPI_TOKEN")
WHAPI_URL = os.getenv("WHAPI_URL", "https://gate.whapi.cloud")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# 2. متغير "تخصص المحل" (X)
# إيلا ما حددتيش المحل، غيخدم كمساعد ذكي عام
STORE_CONTEXT = os.getenv("STORE_CONTEXT", "أنت مساعد ذكي، محترف، ومؤدب. أجب باختصار بالدارجة المغربية.")

# إعداد العقل المدبر
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')

# فحص حالة السيرفر
@app.route('/', methods=['GET'])
def home():
    return "🚀 Nadi.ai is running perfectly on the Cloud!", 200

# قنطرة استقبال الرسائل (Webhook)
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
        if not data or 'messages' not in data:
            return jsonify({"status": "ignored"}), 200

        for message in data['messages']:
            # تجاهل الرسائل اللي صيفطناها حنا أو رسائل المجموعات
            if message.get('from_me') or 'chat_id' not in message:
                continue
            
            sender = message['chat_id']
            text = message.get('text', {}).get('body', '').strip()

            if not text:
                continue

            print(f"📩 رسالة من {sender}: {text}")

            # أ. إرسال إشارة "يكتب..." (Typing) لاحترافية أكثر
            requests.post(
                f"{WHAPI_URL}/messages/text",
                headers={"Authorization": f"Bearer {WHAPI_TOKEN}"},
                json={"to": sender, "typing_time": 3}
            )

            # ب. سؤال Gemini مع دمج "تخصص المحل"
            prompt = f"{STORE_CONTEXT}\nسؤال الزبون: {text}"
            response = model.generate_content(prompt)
            reply = response.text.strip()

            # ج. إرسال الجواب للواتساب
            requests.post(
                f"{WHAPI_URL}/messages/text",
                headers={"Authorization": f"Bearer {WHAPI_TOKEN}"},
                json={"to": sender, "body": reply}
            )

            # د. تسجيل المحادثة في الذاكرة (Supabase)
            if SUPABASE_URL and SUPABASE_KEY:
                db_headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}
                db_payload = {"message": f"User: {text} | Bot: {reply}"}
                requests.post(f"{SUPABASE_URL}/rest/v1/test_nadi", headers=db_headers, json=db_payload)

        # ديما كنرجعو 200 باش Whapi يعرف بلي وصلنا الميساج
        return jsonify({"status": "success"}), 200

    except Exception as e:
        print(f"❌ خطأ تقني: {e}")
        return jsonify({"status": "error", "message": str(e)}), 200

if __name__ == '__main__':
    # البورت الديناميكي باش يخدم في Render بلا مشاكل
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
