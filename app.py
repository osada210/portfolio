import urllib.request
from bs4 import BeautifulSoup
import json
import requests
import re
import requests_cache
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient, Configuration, MessagingApi,
    ReplyMessageRequest, TextMessage
)
from linebot.v3.webhooks import (
    MessageEvent, TextMessageContent
)
import os

from dotenv import load_dotenv
load_dotenv()

CHANNEL_ACCESS_TOKEN = os.environ["CHANNEL_ACCESS_TOKEN"]
CHANNEL_SECRET = os.environ["CHANNEL_SECRET"]

app = Flask(__name__)
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# キャッシュ設定（60分間キャッシュを保存）
requests_cache.install_cache('anime_cache', expire_after=3600)

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

        def a_result(ttl, img, data):
            results = []
            for i in range(len(ttl)):
                title = ttl[i].get_text()
                imagine = img[i] if i < len(img) else "画像なし"
                overview = data[i].get_text()
                results.append(f"{title}\n{imagine}\n{overview}\n")
            return results

        anime_result = a_result(ttl=anime_Ttl, img=anime_Img, data=anime_data)

        # メッセージをまとめて送信可能な長さに調整
        message_text = "\n\n".join(anime_result[:5])  # 最初の5件のみ送信（長すぎるとエラーになるため）
        
        line_bot_api.reply_message(ReplyMessageRequest(
            replyToken=event.reply_token,
            messages=[TextMessage(text=message_text)]
        ))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
