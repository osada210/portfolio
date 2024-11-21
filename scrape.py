import urllib.request
from bs4 import BeautifulSoup
import json
import requests
import re

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
def result(ttl,img,data):
  results = []
  for i in range(len(ttl)):
    title = ttl[i].get_text()
    imagine = img[i]
    overview = data[i].get_text()
    anime_result = title + imagine + overview
    results.append(anime_result)
  return results

def get_anime_results():
    return result(ttl=anime_Ttl, img=anime_Img, data=anime_data)