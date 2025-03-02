import logging
import requests
from bs4 import BeautifulSoup
import os
import time
from flask import Flask, request, abort
from cachetools import TTLCache
from dotenv import load_dotenv
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient, Configuration, MessagingApi,
    ReplyMessageRequest, FlexMessage
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

# .env 読み込み
load_dotenv()
CHANNEL_ACCESS_TOKEN = os.environ["CHANNEL_ACCESS_TOKEN"]
CHANNEL_SECRET = os.environ["CHANNEL_SECRET"]

# Flask アプリ設定
app = Flask(__name__)
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# ロギング設定
logging.basicConfig(level=logging.INFO)

# キャッシュ（10分間保持、最大1セットのデータを保存）
anime_cache = TTLCache(maxsize=1, ttl=600)


@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature.")
        abort(400)
    
    return 'OK'


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

    received_message = event.message.text.strip()

    if received_message == "@anime":
        try:
            # キャッシュがあるか確認
            if "anime_data" in anime_cache:
                logging.info("キャッシュを使用")
                anime_result = anime_cache["anime_data"]
            else:
                logging.info("スクレイピング開始")
                anime_result = fetch_anime_data()
                anime_cache["anime_data"] = anime_result  # キャッシュに保存

            # フレックスメッセージの作成
            flex_message = create_flex_message(anime_result)

            line_bot_api.reply_message(
                ReplyMessageRequest(replyToken=event.reply_token, messages=[flex_message])
            )

        except Exception as e:
            logging.error(f"Error: {e}")
            line_bot_api.reply_message(
                ReplyMessageRequest(replyToken=event.reply_token, messages=[TextMessage(text="エラーが発生しました。")])
            )


def fetch_anime_data():
    """アニメ情報をスクレイピングして取得する"""
    res = requests.get('https://anime.eiga.com/program/')
    soup = BeautifulSoup(res.text, 'html.parser')

    anime_titles = soup.find_all(class_="seasonAnimeTtl")
    anime_images = soup.find_all("img")
    anime_details = soup.find_all(class_="seasonAnimeDetail")

    # 重複削除関数
    def dedup_and_restore(data):
        reversed_data = data[::-1]
        unique_reversed = sorted(set(reversed_data), key=reversed_data.index)
        return unique_reversed[::-1]

    anime_titles = dedup_and_restore(anime_titles)
    anime_images = dedup_and_restore(anime_images)
    anime_images = [
        img.get("src") for img in anime_images
        if img.get("src") and ("/program/" in img.get("src") or "/shared/" in img.get("src"))
    ]

    # データをフォーマット
    def format_anime_data(titles, images, details):
        results = []
        for i in range(min(len(titles), 10)):  # 最大10件
            title = titles[i].get_text().strip()
            image = images[i] if i < len(images) else "No image"
            overview = details[i].get_text().strip() if i < len(details) else "No description"

            results.append({
                "title": title,
                "image": image,
                "overview": overview
            })
        return results

    return format_anime_data(anime_titles, anime_images, anime_details)


def create_flex_message(anime_list):
    """アニメ情報をFlex Message形式に変換する"""
    contents = []
    for anime in anime_list:
        contents.append({
            "type": "bubble",
            "hero": {
                "type": "image",
                "url": anime["image"],
                "size": "full",
                "aspectRatio": "20:13",
                "aspectMode": "cover"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": anime["title"], "weight": "bold", "size": "lg"},
                    {"type": "text", "text": anime["overview"], "wrap": True, "size": "sm"}
                ]
            }
        })

    return FlexMessage(alt_text="最新アニメ情報", contents={"type": "carousel", "contents": contents})


## ボット起動コード
if __name__ == "__main__":
    ## ローカルでテストする時のために、`debug=True` にしておく
    app.run(host="0.0.0.0", port=8000, debug=True)

