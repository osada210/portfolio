import logging

# ロギングの設定
logging.basicConfig(level=logging.INFO)

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

    received_message = event.message.text

    if received_message == "@anime":
        try:
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
                    title = ttl[i].get_text().strip()
                    imagine = img[i] if i < len(img) else "No image"
                    overview = data[i].get_text().strip() if i < len(data) else "No description"
                    anime_result = f"【タイトル】{title}\n【画像URL】{imagine}\n【概要】{overview}"
                    results.append(anime_result)
                return results

            anime_result = a_result(ttl=anime_Ttl, img=anime_Img, data=anime_data)

            # 応答メッセージの長さに注意
            reply_messages = [TextMessage(text=result[:1000]) for result in anime_result[:5]]

            line_bot_api.reply_message(
                ReplyMessageRequest(replyToken=event.reply_token, messages=reply_messages)
            )

        except Exception as e:
            logging.error(f"Error in handle_message: {e}")
            line_bot_api.reply_message(
                ReplyMessageRequest(replyToken=event.reply_token, messages=[TextMessage(text="エラーが発生しました。")])
            )



## ボット起動コード
if __name__ == "__main__":
    ## ローカルでテストする時のために、`debug=True` にしておく
    app.run(host="0.0.0.0", port=8000, debug=True)

