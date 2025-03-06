import os
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient, Configuration, MessagingApi,
    ReplyMessageRequest, FlexMessage, FlexCarousel, FlexBubble, FlexBox, FlexText, FlexImage
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from dotenv import load_dotenv

# .env ファイルの読み込み
load_dotenv()

# 環境変数の取得
CHANNEL_ACCESS_TOKEN = os.environ["CHANNEL_ACCESS_TOKEN"]
CHANNEL_SECRET = os.environ["CHANNEL_SECRET"]

# Flask アプリのインスタンス化
app = Flask(__name__)

# LINE のアクセストークン設定
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# コールバック関数
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

# アニメのフレックスメッセージ（カルーセル）を作成
def create_anime_flex_message():
    # 各アニメの情報
    anime_data = [
        {
            "title": "阿波連さんははかれない season2",
            "release": "2025年春放送予定",
            "image_url": "https://eiga.k-img.com/images/anime/program/112373/photo/12fd5ed30a0b7467/160.jpg?1722832556",
            "studio": "FelixFilm",
            "staff": "総監督: 山本靖貴\n監督: 牧野友映\nシリーズ構成: 吉岡たかを",
            "cast": "水瀬いのり, 寺島拓篤, M・A・O, 柿原徹也, 楠木ともり, 花澤香菜"
        },
        {
            "title": "リゼロ season3",
            "release": "2024年10月放送予定",
            "image_url": "https://animeanime.jp/imgs/zoom/472579.jpg",
            "studio": "WHITE FOX",
            "staff": "監督: 渡邊政治\nシリーズ構成: 横谷昌宏",
            "cast": "小林裕介, 高橋李依, 内山夕実, 水瀬いのり"
        }
    ]

    # 各アニメの情報を元にバブルを作成
    bubbles = []
    for anime in anime_data:
        bubble = FlexBubble(
            size='giga',
            header=FlexBox(
                layout='vertical',
                contents=[
                    FlexText(text=f"【{anime['title']}】", color='#FFFFFF', size='xl', weight='bold'),
                    FlexText(text=anime['release'], color='#FFFFFF66', size='lg')
                ],
                spacing='sm',
                backgroundColor='#0367D3',
                paddingAll='xxl'
            ),
            body=FlexBox(
                layout='vertical',
                spacing='xxl',
                contents=[
                    FlexImage(url=anime['image_url'], size='full', aspect_ratio="1:1", aspect_mode="cover"),
                    FlexText(text=f"制作会社: {anime['studio']}", size='lg', wrap=True),
                    FlexText(text="メインスタッフ:", size='lg', wrap=True),
                    FlexText(text=anime['staff'], size='lg', wrap=True),
                    FlexText(text="メインキャスト:", size='lg', wrap=True),
                    FlexText(text=anime['cast'], size='lg', wrap=True)
                ]
            )
        )
        bubbles.append(bubble)

    # カルーセルメッセージを作成
    return FlexMessage(
        alt_text="最新アニメ情報",
        contents=FlexCarousel(contents=bubbles)
    )

# ユーザーのメッセージを受け取る
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

    received_message = event.message.text

    # "@anime" のメッセージが送られた場合、カルーセル形式のフレックスメッセージを送信
    if received_message == "@anime":
        message = create_anime_flex_message()
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[message]
            )
        )

# アプリケーション起動
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)


