from flask import Flask, request, jsonify
import requests
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

app = Flask(__name__)

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

@app.route("/run", methods=["POST"])
def run():
    print("[서버] 실행 요청 수신 → 기사 수집 시작")
    today = datetime.now()
    start_date = today - timedelta(days=7)

    summaries = []

    for ministry, url in RSS_FEEDS.items():
        feed = feedparser.parse(url)
        for entry in feed.entries:
            try:
                pub_date = datetime(*entry.published_parsed[:6])
            except Exception:
                continue
            if not (start_date <= pub_date <= today):
                continue

            title = clean_html(entry.get("title", "제목 없음"))
            summary = clean_html(entry.get("summary", ""))
            summaries.append({
                "title": title,
                "ministry": ministry,
                "published": pub_date.strftime("%Y-%m-%d"),
                "content": summary
            })
            print(f"[📰 기사] {pub_date.strftime('%Y-%m-%d')} | {ministry} | {title}")

    print(f"[서버] 최종 수집된 기사 수: {len(summaries)}")

    return jsonify({"summaries": summaries}), 200

@app.route("/", methods=["GET"])
def home():
    return "✅ Server is running."

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)