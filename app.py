import urllib.request
from bs4 import BeautifulSoup
import json
import requests
import re
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient, Configuration, MessagingApi,
    ReplyMessageRequest, PushMessageRequest,
    TextMessage, PostbackAction
)
from linebot.v3.webhooks import (
    FollowEvent, MessageEvent, PostbackEvent, TextMessageContent
)
import os


## .env ファイル読み込み
from dotenv import load_dotenv
load_dotenv()

## 環境変数を変数に割り当て
CHANNEL_ACCESS_TOKEN = os.environ["CHANNEL_ACCESS_TOKEN"]
CHANNEL_SECRET = os.environ["CHANNEL_SECRET"]


## Flask アプリのインスタンス化
app = Flask(__name__)

## LINE のアクセストークン読み込み
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

## コールバックのおまじない
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



@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    ## APIインスタンス化
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

    ## 受信メッセージの中身を取得
    received_message = event.message.text

    if received_message == "@anime":
    ## テキスト返信

        #HTML情報の取得・解析
        res = requests.get('https://anime.eiga.com/program/')
        soup = BeautifulSoup(res.text, 'html.parser')

        # 必要なデータのみ抽出
        animeTtl = (soup.find_all(class_ = "seasonAnimeTtl"))
        animeImg = (soup.find_all("img"))
        anime_data = (soup.find_all(class_ = "seasonAnimeDetail"))


        # 重複している要素を削除
        def dedup_and_restore(data):
            reversed = data[::-1]
            unique_reversed = sorted(set(reversed), key=reversed.index)
            return unique_reversed[::-1]

        anime_Ttl = dedup_and_restore(animeTtl)
        anime_Img = dedup_and_restore(animeImg)
        anime_Img = [img.get("src") for img in anime_Img if img.get("src") and ("/program/" in img.get("src") or "/shared/" in img.get("src"))]

        # データを一つのループで処理
        def a_result(ttl,img,data):
            results = []
            for i in range(len(ttl)):
                title = ttl[i].get_text()
                imagine = img[i]
                overview = data[i].get_text()
                anime_result = title + imagine + overview
                results.append(anime_result)
            return results

        anime_result = a_result(ttl=anime_Ttl, img=anime_Img, data=anime_data)

        line_bot_api.reply_message(ReplyMessageRequest(
            replyToken=event.reply_token,
            messages=[TextMessage(text=anime_result)]
        ))



## ボット起動コード
if __name__ == "__main__":
    ## ローカルでテストする時のために、`debug=True` にしておく
    app.run(host="0.0.0.0", port=8000, debug=True)