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
    ReplyMessageRequest, TextMessage
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
import os
from linebot.v3.messaging import FlexMessage

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

flex_content = {
  "type": "bubble",
  "hero": {
    "type": "image",
    "url": "https://developers-resource.landpress.line.me/fx/img/01_1_cafe.png",
    "size": "full",
    "aspectRatio": "20:13",
    "aspectMode": "cover",
    "action": {
      "type": "uri",
      "uri": "https://line.me/"
    }
  },
  "body": {
    "type": "box",
    "layout": "vertical",
    "contents": [
      {
        "type": "text",
        "text": "Brown Cafe",
        "weight": "bold",
        "size": "xl"
      },
      {
        "type": "box",
        "layout": "baseline",
        "margin": "md",
        "contents": [
          {
            "type": "icon",
            "size": "sm",
            "url": "https://developers-resource.landpress.line.me/fx/img/review_gold_star_28.png"
          },
          {
            "type": "icon",
            "size": "sm",
            "url": "https://developers-resource.landpress.line.me/fx/img/review_gold_star_28.png"
          },
          {
            "type": "icon",
            "size": "sm",
            "url": "https://developers-resource.landpress.line.me/fx/img/review_gold_star_28.png"
          },
          {
            "type": "icon",
            "size": "sm",
            "url": "https://developers-resource.landpress.line.me/fx/img/review_gold_star_28.png"
          },
          {
            "type": "icon",
            "size": "sm",
            "url": "https://developers-resource.landpress.line.me/fx/img/review_gray_star_28.png"
          },
          {
            "type": "text",
            "text": "4.0",
            "size": "sm",
            "color": "#999999",
            "margin": "md",
            "flex": 0
          }
        ]
      },
      {
        "type": "box",
        "layout": "vertical",
        "margin": "lg",
        "spacing": "sm",
        "contents": [
          {
            "type": "box",
            "layout": "baseline",
            "spacing": "sm",
            "contents": [
              {
                "type": "text",
                "text": "Place",
                "color": "#aaaaaa",
                "size": "sm",
                "flex": 1
              },
              {
                "type": "text",
                "text": "Flex Tower, 7-7-4 Midori-ku, Tokyo",
                "wrap": true,
                "color": "#666666",
                "size": "sm",
                "flex": 5
              }
            ]
          },
          {
            "type": "box",
            "layout": "baseline",
            "spacing": "sm",
            "contents": [
              {
                "type": "text",
                "text": "Time",
                "color": "#aaaaaa",
                "size": "sm",
                "flex": 1
              },
              {
                "type": "text",
                "text": "10:00 - 23:00",
                "wrap": true,
                "color": "#666666",
                "size": "sm",
                "flex": 5
              }
            ]
          }
        ]
      }
    ]
  },
  "footer": {
    "type": "box",
    "layout": "vertical",
    "spacing": "sm",
    "contents": [
      {
        "type": "button",
        "style": "link",
        "height": "sm",
        "action": {
          "type": "uri",
          "label": "CALL",
          "uri": "https://line.me/"
        }
      },
      {
        "type": "button",
        "style": "link",
        "height": "sm",
        "action": {
          "type": "uri",
          "label": "WEBSITE",
          "uri": "https://line.me/"
        }
      },
      {
        "type": "box",
        "layout": "vertical",
        "contents": [],
        "margin": "sm"
      }
    ],
    "flex": 0
  }
}


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

    received_message = event.message.text

    if received_message == "@anime":
        # キャッシュがある場合はそれを使用
        if "anime_data" in cache:
            anime_result = cache["anime_data"]
        else:
            # スクレイピングを実行
            anime_result = fetch_anime_data()
            cache["anime_data"] = anime_result  # キャッシュに保存

        # メッセージを整形
        reply_text = "\n\n".join(anime_result[:5])  # 最大5件まで表示
        if not reply_text:
            reply_text = "アニメ情報が取得できませんでした。"

        message = FlexMessage(alt_text="アニメ情報", contents=flex_content)
        line_bot_api.reply_message(ReplyMessageRequest(
            replyToken=event.reply_token,
            messages=[message]
        ))

def fetch_anime_data():
    """アニメ情報をスクレイピングして取得する"""
    res = requests.get('https://anime.eiga.com/program/')
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

    # データ整形
    anime_result = []
    for i in range(min(len(anime_Ttl), 10)):  # 最大10件
        title = anime_Ttl[i].get_text().strip()
        image = anime_Img[i] if i < len(anime_Img) else "No image"
        overview = anime_data[i].get_text().strip() if i < len(anime_data) else "No description"
        anime_result.append(f"【{title}】\n{overview}\n画像: {image}")

    return anime_result

# ボット起動
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
