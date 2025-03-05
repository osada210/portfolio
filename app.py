import os
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient, Configuration, MessagingApi,
    ReplyMessageRequest, TextMessage, FlexMessage
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from dotenv import load_dotenv

# .env ファイル読み込み
load_dotenv()

# 環境変数を変数に割り当て
CHANNEL_ACCESS_TOKEN = os.environ["CHANNEL_ACCESS_TOKEN"]
CHANNEL_SECRET = os.environ["CHANNEL_SECRET"]

# Flask アプリのインスタンス化
app = Flask(__name__)

# LINE のアクセストークン読み込み
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# コールバックのおまじない
@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

# フレックスメッセージの内容
def create_flex_message():
    return FlexMessage(
        alt_text="シンプルなフレックスメッセージ",
        contents={
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
            }
        }
    )


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    # APIインスタンス化
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

    # 受信メッセージの中身を取得
    received_message = event.message.text

    # @test が受信された場合、フレックスメッセージを送信
    if received_message == "@test":
        message = create_flex_message()  # フレックスメッセージの作成
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[message]
            )
        )

# ボット起動
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)

