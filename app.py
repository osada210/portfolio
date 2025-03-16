import os
import requests
import requests_cache
from bs4 import BeautifulSoup
from flask import Flask, request, abort
from dotenv import load_dotenv
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient, Configuration, MessagingApi,
    PushMessageRequest, FlexMessage, FlexCarousel, FlexBubble, FlexBox, FlexText, FlexImage
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
import time

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

# ユーザーのリクエストタイミングを記録する辞書
user_request_times = {}

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

# テキストをフォーマットする関数
def format_anime_info(text):
    # 改行を追加して情報を整理
    formatted_text = text.replace("【", "\n【").replace("】", "】\n").replace("、", "、\n")
    
    # ラベルを調整
    formatted_text = formatted_text.replace("メインスタッフ", "")
    formatted_text = formatted_text.replace("メインキャスト", "\n\nメインキャスト:")

    # 総監督または監督の上にスペースを追加
    if "【総監督】" in formatted_text:
        formatted_text = formatted_text.replace("【総監督】", "\n【総監督】")
    else:
        formatted_text = formatted_text.replace("【監督】", "\n【監督】")

    if "放送開始" in formatted_text:
        formatted_text = formatted_text.replace("放送開始", "\n放送開始: ")
    elif "放送時期" in formatted_text:
        formatted_text = formatted_text.replace("放送時期", "\n放送時期: ")

    return formatted_text.strip()

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
            overview = format_anime_info(data[i].get_text())
            results.append({"title": title, "image": imagine, "overview": overview})
        return results

    return a_result(ttl=anime_Ttl, img=anime_Img, data=anime_data)

# スクレイピングデータをカルーセルに変換する関数
def create_anime_flex_message_from_scraping(start_index=0, count=10):
    anime_list = scrape_anime_data()
    bubbles = []

    for anime in anime_list[start_index:start_index + count]:
        bubble = FlexBubble(
            size='kilo',
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
                    FlexImage(url=anime['image'], size='lg', aspect_ratio="1:1", aspect_mode="cover") if anime['image'] != "画像なし" else FlexText(text="画像なし", size='sm', wrap=True),
                    FlexText(text=anime['overview'], size='sm', wrap=True)
                ]
            )
        )
        bubbles.append(bubble)

    return FlexMessage(
        alt_text="アニメ情報",
        contents=FlexCarousel(contents=bubbles)
    )

# ユーザーのメッセージを受け取る
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_id = event.source.user_id
    received_message = event.message.text

    # ユーザーのリクエスト頻度を制限
    current_time = time.time()
    if user_id in user_request_times:
        last_request_time = user_request_times[user_id]
        if current_time - last_request_time < 10:
            app.logger.info(f"Request from user {user_id} is too frequent.")
            return
    user_request_times[user_id] = current_time

    if received_message == "@anime":
        anime_list = scrape_anime_data()
        messages = []

        # 10件ずつのFlex Messageを作成
        for start_index in range(0, len(anime_list), 10):
            message = create_anime_flex_message_from_scraping(start_index=start_index)
            messages.append(message)

        # すべてのメッセージをプッシュメッセージで送信
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            try:
                # メッセージを5件ずつに分割して送信
                for i in range(0, len(messages), 5):
                    line_bot_api.push_message(
                        PushMessageRequest(
                            to=user_id,
                            messages=messages[i:i+5]
                        )
                    )
            except Exception as e:
                app.logger.error(f"Failed to send push message: {e}")

# アプリケーション起動
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)


#renderのスリープ対策
@app.route("/", methods=['GET'])
def health_check():
    return "OK", 200
