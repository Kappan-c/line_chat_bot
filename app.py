from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent
import configparser
import os
from vertexai.generative_models import GenerativeModel, HarmCategory, HarmBlockThreshold

# 初始化 Flask
app = Flask(__name__)

# 讀取 LINE Bot 配置
config = configparser.ConfigParser()
config.read('config.ini')

configuration = Configuration(access_token=config.get('line-bot', 'channel_access_token'))
handler = WebhookHandler(config.get('line-bot', 'channel_secret'))

# 設定 Google Cloud 認證
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'your_google_credentials.json'

# 初始化 Vertex AI 模型
system_instruction = "妳專責用繁中跟人聊天，語氣像正常的成年人"
model = GenerativeModel('gemini-2.0-flash-exp', system_instruction=system_instruction)

generation_config = {
    'max_output_tokens': 256,
    'temperature': 1.0
}

safety_settings = {
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE
}

# 處理 LINE 訊息
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_message = event.message.text
    chat = model.start_chat()
    response = chat.send_message(user_message, generation_config=generation_config, safety_settings=safety_settings)
    
    reply_token = event.reply_token
    messages = [TextMessage(text=response.text)]
    
    with ApiClient(configuration) as api_client:
        messaging_api = MessagingApi(api_client)
        messaging_api.reply_message(ReplyMessageRequest(reply_token=reply_token, messages=messages))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)