import os
import requests
import requests_cache
import urllib.request
from bs4 import BeautifulSoup
from flask import Flask, request, abort
from dotenv import load_dotenv
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient, Configuration, MessagingApi,
    ReplyMessageRequest, FlexMessage, FlexCarousel, FlexBubble, FlexBox, FlexText, FlexImage, FlexButton
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

# 環境変数の読み込み
load_dotenv()
CHANNEL_ACCESS_TOKEN = os.environ["CHANNEL_ACCESS_TOKEN"]
CHANNEL_SECRET = os.environ["CHANNEL_SECRET"]

# Flask アプリのインスタンス化
app = Flask(__name__)
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# キャッシュ設定（60分間キャッシュを保存）
requests_cache.install_cache('anime_cache', expire_after=3600)

# ユーザーの状態を管理するための辞書
user_states = {}

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

# スクレイピングを行う関数
def scrape_anime_data():
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
            results.append({"title": title, "image": imagine, "overview": overview})
        return results

    return a_result(ttl=anime_Ttl, img=anime_Img, data=anime_data)

# スクレイピングデータをカルーセルに変換する関数
def create_anime_flex_message_from_scraping(start_index=0, count=5):
    anime_list = scrape_anime_data()
    bubbles = []

    for anime in anime_list[start_index:start_index + count]:
        bubble = FlexBubble(
            size='giga',
            header=FlexBox(
                layout='vertical',
                contents=[
                    FlexText(text=f"【{anime['title']}】", color='#FFFFFF', size='xl', weight='bold'),
                ],
                backgroundColor='#0367D3',
                paddingAll='xxl'
            ),
            body=FlexBox(
                layout='vertical',
                spacing='xxl',
                contents=[
                    FlexImage(url=anime['image'], size='full', aspect_ratio="1:1", aspect_mode="cover") if anime['image'] != "画像なし" else FlexText(text="画像なし", size='lg', wrap=True),
                    FlexText(text=anime['overview'], size='lg', wrap=True)
                ]
            ),
            footer=FlexBox(
                layout='vertical',
                contents=[
                    FlexButton(
                        style='primary',
                        color='#0367D3',
                        action={
                            "type": "message",
                            "label": "次を表示",
                            "text": "@next"
                        }
                    )
                ]
            )
        )
        bubbles.append(bubble)

    return FlexMessage(
        alt_text="最新アニメ情報",
        contents=FlexCarousel(contents=bubbles)
    )

# ユーザーのメッセージを受け取る
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

    user_id = event.source.user_id
    received_message = event.message.text

    if received_message == "@anime":
        user_states[user_id] = 0  # 初期インデックスを設定
        message = create_anime_flex_message_from_scraping()
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[message]
            )
        )
    elif received_message == "@next":
        if user_id in user_states:
            user_states[user_id] += 5  # 次のインデックスに進む
            message = create_anime_flex_message_from_scraping(start_index=user_states[user_id])
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    replyToken=event.reply_token,
                    messages=[message]
                )
            )

# アプリケーション起動
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)

