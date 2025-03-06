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
    ReplyMessageRequest, PushMessageRequest, FlexMessage, FlexCarousel, FlexBubble, FlexBox, FlexText, FlexImage
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
def create_anime_flex_message_from_scraping(start_index=0, count=10):
    anime_list = scrape_anime_data()
    bubbles = []

    for anime in anime_list[start_index:start_index + count]:
        bubble = FlexBubble(
            size='mega',  # サイズを小さく設定
            header=FlexBox(
                layout='vertical',
                contents=[
                    FlexText(text=f"【{anime['title']}】", color='#FFFFFF', size='md', weight='bold'),
                ],
                backgroundColor='#0367D3',
                paddingAll='lg'
            ),
            body=FlexBox(
                layout='vertical',
                spacing='md',
                contents=[
                    FlexImage(url=anime['image'], size='full', aspect_ratio="1:1", aspect_mode="cover") if anime['image'] != "画像なし" else FlexText(text="画像なし", size='sm', wrap=True),
                    FlexText(text=anime['overview'], size='sm', wrap=True)
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
    user_id = event.source.user_id
    received_message = event.message.text

    if received_message == "@anime":
        anime_list = scrape_anime_data()
        messages = []

        # 10件ずつのFlex Messageを作成
        for start_index in range(0, len(anime_list), 10):
            message = create_anime_flex_message_from_scraping(start_index=start_index)
            messages.append(message)

        # すべてのメッセージを送信
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            try:
                # 1つのリプライトークンで複数のメッセージを送信する
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        replyToken=event.reply_token,
                        messages=messages
                    )
                )
            except Exception as e:
                app.logger.error(f"Failed to send message with reply token: {e}")
                # リプライトークンが無効な場合、push_messageを使用して再送信
                for message in messages:
                    line_bot_api.push_message(
                        PushMessageRequest(
                            to=user_id,
                            messages=[message]
                        )
                    )

# アプリケーション起動
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)

