from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient, Configuration, MessagingApi,
    ReplyMessageRequest, FlexMessage
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
import os
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# LINE API 設定
CHANNEL_ACCESS_TOKEN = os.environ["CHANNEL_ACCESS_TOKEN"]
CHANNEL_SECRET = os.environ["CHANNEL_SECRET"]
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

def get_anime():
    """ アニメ情報を1件取得 """
    res = requests.get('https://anime.eiga.com/program/', timeout=10)
    soup = BeautifulSoup(res.text, 'html.parser')
    
    title = soup.find(class_="seasonAnimeTtl")
    image = soup.find("img")
    overview = soup.find(class_="seasonAnimeDetail")

    return {
        "title": title.get_text() if title else "タイトル不明",
        "image": image["src"] if image and image.get("src") else "https://via.placeholder.com/300",
        "overview": overview.get_text() if overview else "概要なし"
    }

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    if event.message.text == "@anime":
        anime = get_anime()
        
        flex_content = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": anime["title"], "weight": "bold", "size": "xl", "wrap": True},
                    {"type": "image", "url": anime["image"], "size": "full", "aspectRatio": "16:9", "aspectMode": "cover"},
                    {"type": "text", "text": anime["overview"], "size": "sm", "wrap": True}
                ]
            }
        }

        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            message = FlexMessage(alt_text="アニメ情報", contents=flex_content)
            line_bot_api.reply_message(ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[message]
            ))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)

