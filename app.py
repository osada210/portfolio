import logging
import os
import requests
import json
from bs4 import BeautifulSoup
from cachetools import TTLCache
from dotenv import load_dotenv
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient, Configuration, MessagingApi,
    ReplyMessageRequest, FlexMessage
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

# .env ファイル読み込み
load_dotenv()

# 環境変数
CHANNEL_ACCESS_TOKEN = os.environ["CHANNEL_ACCESS_TOKEN"]
CHANNEL_SECRET = os.environ["CHANNEL_SECRET"]

# Flask アプリ設定
app = Flask(__name__)

# LINE API 設定
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# キャッシュ設定（キー: "anime_data", 保存時間: 600秒＝10分）
cache = TTLCache(maxsize=1, ttl=600)


@app.route("/callback", methods=['POST'])
def callback():
    """LINEのWebhookを受信するエンドポイント"""
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    """メッセージイベントを処理"""
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

    received_message = event.message.text

    if received_message == "@anime":
        try:
            # キャッシュがある場合、スクレイピングせずにキャッシュを使用
            if "anime_data" in cache:
                anime_result = cache["anime_data"]
            else:
                anime_result = fetch_anime_data()
                cache["anime_data"] = anime_result  # キャッシュに保存

            # フレックスメッセージを作成
            flex_message = create_flex_message(anime_result)

            # 返信
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    replyToken=event.reply_token,
                    messages=[flex_message]
                )
            )

        except Exception as e:
            logging.error(f"Error in handle_message: {e}")
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    replyToken=event.reply_token,
                    messages=[TextMessage(text="エラーが発生しました。")]
                )
            )


def fetch_anime_data():
    """アニメ情報をスクレイピングして取得"""
    url = 'https://anime.eiga.com/program/'
    res = requests.get(url)
    soup = BeautifulSoup(res.text, 'html.parser')

    animeTtl = soup.find_all(class_="seasonAnimeTtl")
    animeImg = soup.find_all("img")
    anime_data = soup.find_all(class_="seasonAnimeDetail")

    # 重複削除
    def dedup_and_restore(data):
        reversed_data = data[::-1]
        unique_reversed = sorted(set(reversed_data), key=reversed_data.index)
        return unique_reversed[::-1]

    anime_Ttl = dedup_and_restore(animeTtl)
    anime_Img = dedup_and_restore(animeImg)
    anime_Img = [img.get("src") for img in anime_Img if img.get("src") and ("/program/" in img.get("src") or "/shared/" in img.get("src"))]

    # データ整理
    anime_list = []
    for i in range(min(len(anime_Ttl), 10)):  # 10件まで取得
        title = anime_Ttl[i].get_text().strip()
        image_url = anime_Img[i] if i < len(anime_Img) else "No image"
        overview = anime_data[i].get_text().strip() if i < len(anime_data) else "No description"
        anime_list.append({"title": title, "image": image_url, "overview": overview})

    return anime_list


def create_flex_message(anime_list):
    """フレックスメッセージを生成"""
    bubble_contents = []

    for anime in anime_list:
        bubble = {
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
                    {
                        "type": "text",
                        "text": anime["title"],
                        "weight": "bold",
                        "size": "lg",
                        "wrap": True
                    },
                    {
                        "type": "text",
                        "text": anime["overview"][:60] + "...",  # 概要の一部のみ表示
                        "size": "sm",
                        "wrap": True
                    }
                ]
            }
        }
        bubble_contents.append(bubble)

    flex_message = FlexMessage(
        altText="アニメ情報一覧",
        contents={
            "type": "carousel",
            "contents": bubble_contents
        }
    )

    return flex_message


# Flask サーバー起動
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)


