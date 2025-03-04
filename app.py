from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient, Configuration, MessagingApi,
    ReplyMessageRequest, FlexMessage
)
from linebot.v3.webhooks import PostbackEvent, MessageEvent, TextMessageContent
import os
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

# LINE APIの設定
CHANNEL_ACCESS_TOKEN = os.environ["CHANNEL_ACCESS_TOKEN"]
CHANNEL_SECRET = os.environ["CHANNEL_SECRET"]
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# スクレイピングしたアニメ情報を保存する
anime_data_list = []

def scrape_anime_data():
    global anime_data_list
    if anime_data_list:
        return  # 既にデータがある場合はスクレイピングを行わない
    
    res = requests.get('https://anime.eiga.com/program/')
    soup = BeautifulSoup(res.text, 'html.parser')
    titles = soup.find_all(class_="seasonAnimeTtl")
    images = soup.find_all("img")
    overviews = soup.find_all(class_="seasonAnimeDetail")
    
    anime_data_list = [
        {"title": titles[i].get_text(), "image": images[i]["src"], "overview": overviews[i].get_text()}
        for i in range(min(len(titles), len(images), len(overviews)))
    ]

def create_flex_carousel(start_index):
    bubbles = []
    batch_size = 10
    for i in range(start_index, min(start_index + batch_size, len(anime_data_list))):
        anime = anime_data_list[i]
        bubble = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": anime["title"], "weight": "bold", "size": "xl", "wrap": True},
                    {"type": "image", "url": anime["image"], "size": "full", "aspectRatio": "16:9", "aspectMode": "cover"},
                    {"type": "text", "text": anime["overview"], "size": "sm", "wrap": True}
                ]
            }
        }
        bubbles.append(bubble)
    
    if start_index + batch_size < len(anime_data_list):
        bubbles.append({
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "次のページを見る", "weight": "bold", "size": "lg", "align": "center"}
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "button",
                        "action": {
                            "type": "postback",
                            "label": "次へ",
                            "data": f"page={start_index + batch_size}"
                        }
                    }
                ]
            }
        })
    return {"type": "carousel", "contents": bubbles}

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    if event.message.text == "@anime":
        scrape_anime_data()
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
        flex_content = create_flex_carousel(0)
        message = FlexMessage(alt_text="アニメ情報", contents=flex_content)
        line_bot_api.reply_message(ReplyMessageRequest(
            replyToken=event.reply_token,
            messages=[message]
        ))

@handler.add(PostbackEvent)
def handle_postback(event):
    match = re.match(r"page=(\d+)", event.postback.data)
    if match:
        start_index = int(match.group(1))
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
        flex_content = create_flex_carousel(start_index)
        message = FlexMessage(alt_text="アニメ情報", contents=flex_content)
        line_bot_api.reply_message(ReplyMessageRequest(
            replyToken=event.reply_token,
            messages=[message]
        ))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)

