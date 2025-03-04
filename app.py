import urllib.request
from bs4 import BeautifulSoup
import json
import requests
from flask import Flask, request, abort
from cachetools import TTLCache
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient, Configuration, MessagingApi,
    ReplyMessageRequest, FlexMessage
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
import os

# .env 読み込み
from dotenv import load_dotenv
load_dotenv()

# 環境変数を取得
CHANNEL_ACCESS_TOKEN = os.environ["CHANNEL_ACCESS_TOKEN"]
CHANNEL_SECRET = os.environ["CHANNEL_SECRET"]

# Flask アプリのインスタンス化
app = Flask(__name__)

# LINE のアクセストークン読み込み
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# キャッシュ設定（キー: "anime_data", 保存時間: 600秒＝10分）
cache = TTLCache(maxsize=1, ttl=600)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

    received_message = event.message.text

    if received_message == "@anime":
        if "anime_data" in cache:
            anime_result = cache["anime_data"]
        else:
            anime_result = fetch_anime_data()
            cache["anime_data"] = anime_result

        if not anime_result:
            reply_text = "アニメ情報が取得できませんでした。"
            line_bot_api.reply_message(ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            ))
            return

        # 最初の1件をFlex Messageで送信
        flex_message = create_flex_message(anime_result[0])
        line_bot_api.reply_message(ReplyMessageRequest(
            replyToken=event.reply_token,
            messages=[flex_message]
        ))

def fetch_anime_data():
    """アニメ情報をスクレイピングして取得する"""
    res = requests.get('https://anime.eiga.com/program/')
    soup = BeautifulSoup(res.text, 'html.parser')

    animeTtl = soup.find_all(class_="seasonAnimeTtl")
    animeImg = soup.find_all("img")
    anime_data = soup.find_all(class_="seasonAnimeDetail")

    def dedup_and_restore(data):
        reversed_data = data[::-1]
        unique_reversed = sorted(set(reversed_data), key=reversed_data.index)
        return unique_reversed[::-1]

    anime_Ttl = dedup_and_restore(animeTtl)
    anime_Img = dedup_and_restore(animeImg)
    anime_Img = [img.get("src") for img in anime_Img if img.get("src") and ("/program/" in img.get("src") or "/shared/" in img.get("src"))]

    anime_result = []
    for i in range(min(len(anime_Ttl), 10)):
        title = anime_Ttl[i].get_text().strip()
        image = anime_Img[i] if i < len(anime_Img) else "No image"
        overview = anime_data[i].get_text().strip() if i < len(anime_data) else "No description"
        anime_result.append({"title": title, "image": image, "overview": overview})

    return anime_result

def create_flex_message(anime):
    """Flex Message の JSON を生成"""
    flex_content = {
        "type": "bubble",
        "hero": {
            "type": "image",
            "url": anime["image"],
            "size": "full",
            "aspectRatio": "16:9",
            "aspectMode": "cover"
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": anime["title"],
                    "weight": "bold",
                    "size": "xl",
                    "wrap": True
                },
                {
                    "type": "text",
                    "text": anime["overview"],
                    "size": "sm",
                    "wrap": True,
                    "margin": "md"
                }
            ]
        }
    }

    return FlexMessage(alt_text="最新アニメ情報", contents=flex_content)

# ボット起動
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)

