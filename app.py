
from flask import Flask, request, jsonify
import requests
import feedparser
from bs4 import BeautifulSoup

app = Flask(__name__)

MAKE_WEBHOOK_URL = "https://hook.eu2.make.com/9b4qy33mhkc3qtd64nzs0pcqoft6l4ee"

RSS_FEEDS = {
    "기획재정부": "https://www.korea.kr/rss/dept_moef.xml",
    "보건복지부": "https://www.korea.kr/rss/dept_mw.xml",
    "중소벤처기업부": "https://www.korea.kr/rss/dept_mss.xml",
    "고용노동부": "https://www.korea.kr/rss/dept_moel.xml",
    "외교부": "https://www.korea.kr/rss/dept_mofa.xml",
    "교육부": "https://www.korea.kr/rss/dept_moe.xml",
    "국토교통부": "https://www.korea.kr/rss/dept_molit.xml",
    "환경부": "https://www.korea.kr/rss/dept_me.xml"
}

def clean_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    return soup.get_text().replace("\xa0", " ").strip()

def fetch_articles():
    results = []
    for ministry, url in RSS_FEEDS.items():
        feed = feedparser.parse(url)
        for entry in feed.entries:
            if 'published' not in entry:
                continue
            published = entry.published[:10]
            title = clean_html(entry.title)
            summary = clean_html(entry.summary)
            results.append({
                "ministry": ministry,
                "title": title,
                "content": summary,
                "published": published
            })
    return results

def send_to_make(articles):
    try:
        response = requests.post(MAKE_WEBHOOK_URL, json=articles)
        print(f"[서버] Webhook 전송 결과: {response.status_code}")
        print(f"[서버] 전송된 기사 수: {len(articles)}")
    except Exception as e:
        print(f"[서버] Webhook 전송 실패: {e}")

@app.route("/run", methods=["POST"])
def run():
    print("\n[서버] 실행 요청 수신 → 기사 수집 시작")
    articles = fetch_articles()
    print(f"[서버] 필터링된 기사 수: {len(articles)}")
    send_to_make(articles)
    print("[서버] Make로 전송 완료 ✅")
    return jsonify({"status": "ok", "count": len(articles)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
