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
from linebot.v3.messaging import FlexBubble, FlexBox, FlexText ,FlexMessage, FlexImage

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

# アニメのフレックスメッセージ作成
def create_anime_flex_message():
    # 1つ目のバブル
    bubble_1 = FlexBubble(size='giga')

    # ヘッダー部
    title_text_1 = FlexText(text="阿波連さんははかれない season2", color='#FFFFFF', size='xl', weight='bold')  # タイトル
    subtitle_text_1 = FlexText(text="2025年春放送予定", color='#FFFFFF66', size='lg')  # サブタイトル
    header_box_1 = FlexBox(
        layout='vertical',
        contents=[title_text_1, subtitle_text_1],
        spacing='sm',
        backgroundColor='#0367D3',
        paddingAll='xxl'
    )
    bubble_1.header = header_box_1

    # ボディ部
    body_box_1 = FlexBox(
        layout='vertical',
        spacing='xxl',
        contents=[
            FlexImage(
                url="https://eiga.k-img.com/images/anime/program/112373/photo/12fd5ed30a0b7467/160.jpg?1722832556",  # アニメ画像
                size='full',  # 画像サイズ
                aspect_ratio="1:1",  # アスペクト比
                aspect_mode="cover"  # 画像のトリミング方法
            ),
            FlexText(text="制作会社: FelixFilm", size='lg', wrap=True),
            FlexText(text="メインスタッフ: ", size='lg', wrap=True),
            FlexText(text="総監督: 山本靖貴\n監督: 牧野友映\nシリーズ構成: 吉岡たかを\nキャラクターデザイン: 八尋裕子", size='lg', wrap=True),
            FlexText(text="メインキャスト: 水瀬いのり, 寺島拓篤, M・A・O, 柿原徹也, 楠木ともり, 花澤香菜", size='lg', wrap=True)
        ]
    )
    bubble_1.body = body_box_1

    # 2つ目のバブル（例）
    bubble_2 = FlexBubble(size='giga')

    # ヘッダー部
    title_text_2 = FlexText(text="阿波連さんははかれない season2", color='#FFFFFF', size='xl', weight='bold')  # タイトル
    subtitle_text_2 = FlexText(text="2025年春放送予定", color='#FFFFFF66', size='lg')  # サブタイトル
    header_box_2 = FlexBox(
        layout='vertical',
        contents=[title_text_2, subtitle_text_2],
        spacing='sm',
        backgroundColor='#0367D3',
        paddingAll='xxl'
    )
    bubble_2.header = header_box_2

    # ボディ部
    body_box_2 = FlexBox(
        layout='vertical',
        spacing='xxl',
        contents=[
            FlexText(text="詳細な情報をお楽しみください", size='lg', wrap=True),
            FlexText(text="アニメの詳細なストーリーや制作背景などが待っています", size='lg', wrap=True)
        ]
    )
    bubble_2.body = body_box_2

    # FlexMessage（カルーセル形式）でラップ
    return FlexMessage(
        alt_text="阿波連さんははかれない season2の詳細",  # フレックスメッセージがサポートされていない端末用のテキスト
        contents={
            "type": "carousel",
            "contents": [bubble_1.to_dict(), bubble_2.to_dict()]  # `to_dict()` メソッドでオブジェクトを辞書に変換
        }
    )

# メッセージ受信時の処理
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    # APIインスタンス化
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

    # 受信メッセージの中身を取得
    received_message = event.message.text

    # @test が受信された場合、アニメのフレックスメッセージを送信
    if received_message == "@test":
        message = create_anime_flex_message()  # アニメのフレックスメッセージを作成
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[message]
            )
        )

# ボット起動
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)


