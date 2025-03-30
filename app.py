
from flask import Flask, request, jsonify
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging
import os

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

MAKE_WEBHOOK_URL = os.getenv("MAKE_WEBHOOK_URL") or "https://hook.eu2.make.com/여기에-당신의-수신-웹훅"

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

def clean_html(raw_html):
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text(separator=" ", strip=True)

@app.route("/run", methods=["POST"])
def run():
    logging.info("[서버] 실행 요청 수신 → 기사 수집 시작")

    today = datetime.now()
    start_date = today - timedelta(days=7)

    summaries = []
    for ministry, url in RSS_FEEDS.items():
        feed = feedparser.parse(url)
        for entry in feed.entries:
            try:
                pub_date = datetime(*entry.published_parsed[:6])
            except AttributeError:
                continue
            if not (start_date <= pub_date <= today):
                continue

            title = entry.title
            summary = entry.summary if hasattr(entry, "summary") else ""
            link = entry.link
            try:
                html = requests.get(link, timeout=5).text
                content = clean_html(html)
            except:
                content = summary or "내용 없음"

            summaries.append({
                "title": title,
                "ministry": ministry,
                "published": pub_date.strftime("%Y-%m-%d"),
                "content": content
            })

            logging.info(f"[📰 기사] {pub_date.strftime('%Y-%m-%d')} | {ministry} | {title}")

    if not summaries:
        logging.info("[서버] 전송할 요약 없음")
        return jsonify({"status": "no data"}), 200

    logging.info("[서버] Webhook 전송 시도")
    res = requests.post(MAKE_WEBHOOK_URL, json={"summaries": summaries})
    logging.info(f"[서버] Webhook 전송 결과: {res.status_code}")

    return jsonify({"status": "success", "count": len(summaries)}), 200

if __name__ == "__main__":
    app.run(debug=True)
