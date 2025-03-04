from flask import Flask, request, abort
from linebot.v3 import WebhookHandler, LineBotApi
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.messaging import ReplyMessageRequest, TextMessage, FlexMessage
import requests
import os

app = Flask(__name__)

# LINE API の設定
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

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
    user_message = event.message.text.strip()
    if user_message.lower() == "@anime":
        reply = get_anime_info()
    else:
        reply = TextMessage(text="@anime と送信すると、最新のアニメ情報を取得できます。")
    
    line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[reply]
        )
    )

def get_anime_info():
    api_url = "https://api.example.com/anime"  # APIエンドポイントを適宜変更
    response = requests.get(api_url)
    if response.status_code != 200:
        return TextMessage(text="アニメ情報の取得に失敗しました。")
    
    anime_result = response.json()
    if not anime_result:
        return TextMessage(text="現在、取得できるアニメ情報がありません。")
    
    bubbles = []
    for anime in anime_result[:5]:  # 最大5件表示
        title = anime.get("title", "タイトル不明")
        image_url = anime.get("image", "https://example.com/default.jpg")
        overview = anime.get("overview", "説明なし")
        
        bubble = {
            "type": "bubble",
            "hero": {
                "type": "image",
                "url": image_url,
                "size": "full",
                "aspectRatio": "20:13",
                "aspectMode": "cover"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": title, "weight": "bold", "size": "xl"},
                    {"type": "text", "text": overview, "wrap": True, "size": "sm", "margin": "md"}
                ]
            }
        }
        bubbles.append(bubble)
    
    flex_message = FlexMessage(
        alt_text="アニメ情報",
        contents={
            "type": "carousel",
            "contents": bubbles
        }
    )
    return flex_message

if __name__ == "__main__":
    app.run(debug=True)

