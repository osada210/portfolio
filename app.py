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
    ReplyMessageRequest, TextMessage, FlexMessage
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
import os
from dotenv import load_dotenv

# .env 読み込み
load_dotenv()

# 環境変数を取得
CHANNEL_ACCESS_TOKEN = os.environ["CHANNEL_ACCESS_TOKEN"]
CHANNEL_SECRET = os.environ["CHANNEL_SECRET"]

# Flask アプリのインスタンス化
app = Flask(__name__)

# LINE のアクセストークン読み込み
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

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

# フレックスメッセージの内容
flex_content = {
  "type": "bubble",
  "hero": {
    "type": "image",
    "url": "https://eiga.k-img.com/images/anime/program/112402/photo/32b8213a9a89c167/160.jpg?1740713414",
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
        "text": "TITLE",
        "weight": "bold",
        "size": "xl"
      },
      {
        "type": "text",
        "text": "DESCRIPTION",
        "wrap": True,
        "size": "sm"
      }
    ]
  },
  "footer": {  # フッター部分を追加
    "type": "box",
    "layout": "horizontal",
    "contents": [
      {
        "type": "button",
        "style": "primary",
        "action": {
          "type": "uri",
          "label": "Learn more",
          "uri": "https://example.com"
        }
      }
    ]
  }
}


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

    received_message = event.message.text

    if received_message == "@anime":
        message = FlexMessage(
            alt_text="アニメ情報",
            contents=flex_content  # フレックスメッセージの内容
        )

        line_bot_api.reply_message(ReplyMessageRequest(
            replyToken=event.reply_token,
            messages=[message]
        ))

# ボット起動
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)

