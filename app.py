import os
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient, Configuration, MessagingApi,
    ReplyMessageRequest, FlexMessage
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from dotenv import load_dotenv
from linebot.v3.messaging import FlexBubble, FlexBox, FlexText

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

# シンプルなフレックスメッセージの作成
def create_simple_flex_message():
    # フレックスメッセージ作成（シンプルな内容）
    bubble_container = FlexBubble(size='giga')

    # ヘッダー部
    title_text = FlexText(text="シンプルなタイトル", color='#FFFFFF', size='xl', weight='bold')
    subtitle_text = FlexText(text="シンプルな説明", color='#FFFFFF66', size='lg')
    header_box = FlexBox(
        layout='vertical',
        contents=[title_text, subtitle_text],
        spacing='sm',
        backgroundColor='#0367D3',
        paddingAll='xxl'
    )
    bubble_container.header = header_box

    # ボディ部
    body_box = FlexBox(
        layout='vertical',
        spacing='xxl',
        contents=[FlexText(text="これはシンプルなフレックスメッセージです。", size='lg', wrap=True)]
    )
    bubble_container.body = body_box

    # FlexMessageでラップ
    return FlexMessage(
        alt_text="シンプルなフレックスメッセージ",
        contents=bubble_container
    )

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    # APIインスタンス化
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

    # 受信メッセージの中身を取得
    received_message = event.message.text

    # @test が受信された場合、シンプルなフレックスメッセージを送信
    if received_message == "@test":
        message = create_simple_flex_message()  # シンプルなフレックスメッセージを作成
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[message]
            )
        )

# ボット起動
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)

