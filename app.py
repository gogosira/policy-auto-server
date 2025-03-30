import os
import feedparser
import requests
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

app = Flask(__name__)

# 8개 부처 RSS 주소
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

# 텍스트 요약용 함수
def clean_html(html_text):
    return BeautifulSoup(html_text, "html.parser").get_text()

def summarize_articles(entries, ministry, max_articles=3):
    summaries = []
    for entry in entries[:max_articles]:
        published = entry.get("published", "")
        try:
            pub_date = datetime.strptime(published[:16], "%a, %d %b %Y")
        except:
            continue

        content = clean_html(entry.get("summary", ""))
        summaries.append({
            "title": entry.get("title", "제목 없음"),
            "ministry": ministry,
            "published": pub_date.strftime("%Y-%m-%d"),
            "content": content
        })
    return summaries

@app.route("/run", methods=["POST"])
def run_script():
    print("[서버] 실행 요청 수신 → 기사 수집 시작")

    today = datetime.now()
    start_date = today - timedelta(days=7)  # 최근 7일
    summaries = []

    for ministry, url in RSS_FEEDS.items():
        feed = feedparser.parse(url)
        filtered = []
        for entry in feed.entries:
            try:
                pub_date = datetime.strptime(entry.published[:16], "%a, %d %b %Y")
                if start_date <= pub_date <= today:
                    filtered.append(entry)
            except:
                continue

        print(f"📌 {ministry} 기사 수집: {len(filtered)}건")
        ministry_summaries = summarize_articles(filtered, ministry)
        summaries.extend(ministry_summaries)

    print(f"✅ 전체 기사 수: {len(summaries)}")

    # Webhook 전송
    make_webhook = os.getenv("MAKE_WEBHOOK_URL")
    if make_webhook:
        res = requests.post(make_webhook, json={"summaries": summaries})
        print(f"📤 Webhook 전송 결과: {res.status_code}")
    else:
        print("❌ MAKE_WEBHOOK_URL 환경변수 없음")

    return jsonify({"count": len(summaries)})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)