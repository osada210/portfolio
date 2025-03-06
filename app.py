from linebot.v3.messaging import FlexCarousel

def create_anime_carousel_message():
    # バブル1
    bubble_1 = FlexBubble(size='giga')
    bubble_1.header = FlexBox(
        layout='vertical',
        contents=[
            FlexText(text="【阿波連さんははかれない season2】", color='#FFFFFF', size='xl', weight='bold'),
            FlexText(text="2025年春放送予定", color='#FFFFFF66', size='lg')
        ],
        spacing='sm',
        backgroundColor='#0367D3',
        paddingAll='xxl'
    )
    bubble_1.body = FlexBox(
        layout='vertical',
        spacing='xxl',
        contents=[
            FlexImage(
                url="https://eiga.k-img.com/images/anime/program/112373/photo/12fd5ed30a0b7467/160.jpg?1722832556",
                size='full',
                aspect_ratio="1:1",
                aspect_mode="cover"
            ),
            FlexText(text="制作会社: FelixFilm", size='lg', wrap=True),
            FlexText(text="放送時期: 2025年春", size='lg', wrap=True)
        ]
    )

    # バブル2（別のアニメ）
    bubble_2 = FlexBubble(size='giga')
    bubble_2.header = FlexBox(
        layout='vertical',
        contents=[
            FlexText(text="【リコリス・リコイル season2】", color='#FFFFFF', size='xl', weight='bold'),
            FlexText(text="2025年夏放送予定", color='#FFFFFF66', size='lg')
        ],
        spacing='sm',
        backgroundColor='#D32F2F',
        paddingAll='xxl'
    )
    bubble_2.body = FlexBox(
        layout='vertical',
        spacing='xxl',
        contents=[
            FlexImage(
                url="https://example.com/licorice.jpg",
                size='full',
                aspect_ratio="1:1",
                aspect_mode="cover"
            ),
            FlexText(text="制作会社: A-1 Pictures", size='lg', wrap=True),
            FlexText(text="放送時期: 2025年夏", size='lg', wrap=True)
        ]
    )

    # カルーセルを作成
    carousel = FlexCarousel(contents=[bubble_1, bubble_2])

    # FlexMessageでラップ
    return FlexMessage(
        alt_text="2025年放送予定のアニメ情報",
        contents=carousel
    )

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

    received_message = event.message.text

    if received_message == "@test":
        message = create_anime_carousel_message()  # カルーセル形式のメッセージ作成
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[message]
            )
        )



