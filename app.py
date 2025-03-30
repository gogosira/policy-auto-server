
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import feedparser
import requests
import pytz
import openai
import os

app = Flask(__name__)

openai.api_key = os.environ.get("OPENAI_API_KEY")

rss_urls = {
    "기획재정부": "https://www.korea.kr/rss/dept_moef.xml",
    "보건복지부": "https://www.korea.kr/rss/dept_mw.xml",
    "중소벤처기업부": "https://www.korea.kr/rss/dept_mss.xml",
    "고용노동부": "https://www.korea.kr/rss/dept_moel.xml",
    "외교부": "https://www.korea.kr/rss/dept_mofa.xml",
    "교육부": "https://www.korea.kr/rss/dept_moe.xml",
    "국토교통부": "https://www.korea.kr/rss/dept_molit.xml",
    "환경부": "https://www.korea.kr/rss/dept_me.xml"
}

WEBHOOK_URL = os.environ.get("MAKE_WEBHOOK_URL")

@app.route("/run", methods=["POST"])
def run():
    print("[서버] 실행 요청 수신 → 기사 수집 시작")
    today = datetime.now(pytz.timezone('Asia/Seoul'))
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=4)

    articles = []

    for ministry, url in rss_urls.items():
        feed = feedparser.parse(url)
        for entry in feed.entries[:5]:
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                pub_date = datetime(*entry.published_parsed[:6], tzinfo=pytz.utc).astimezone(pytz.timezone('Asia/Seoul'))
                print(f"[📰 기사] {pub_date.strftime('%Y-%m-%d')} | {ministry} | {entry.title}")
                
                if pub_date.year < 2024:
                    continue
                if not (start_of_week.date() <= pub_date.date() <= end_of_week.date()):
                    continue
            else:
                continue

            try:
                res = requests.get(entry.link, timeout=5)
                soup = BeautifulSoup(res.text, "html.parser")
                content_area = soup.find("div", class_="view-article")
                content = content_area.get_text(separator="\n", strip=True) if content_area else "(본문 없음)"
                articles.append({
                    "ministry": ministry,
                    "title": entry.title,
                    "link": entry.link,
                    "published": pub_date.strftime("%Y-%m-%d"),
                    "content": content
                })
            except Exception as e:
                print(f"[❌ 오류] {entry.link} 수집 실패: {e}")

    print(f"[서버] 수집된 기사 수: {len(articles)}")

    summaries = []
    for article in articles:
        prompt = f"""
        [기사 제목]
        {article['title']}

        [기사 본문]
        {article['content'][:1000]}

        위 기사의 핵심 내용을 1~2문장으로 요약해줘. 문체는 간결하고 직관적으로, 타겟은 40~60대야.
        """
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}]
            )
            summary = response.choices[0].message.content.strip()
            summaries.append({
                "제목": article['title'],
                "요약": summary,
                "날짜": article['published']
            })
        except Exception as e:
            print(f"[GPT 요약 실패] {article['title']} → {e}")

    print(f"[서버] GPT 요약 완료: {len(summaries)}건")

    if summaries:
        print("[서버] Webhook 전송 시도")
        try:
            res = requests.post(WEBHOOK_URL, json={"summaries": summaries})
            print("[서버] 결과 전송 완료 → 응답코드:", res.status_code)
        except Exception as e:
            print("[서버] Webhook 전송 실패:", e)
    else:
        print("[서버] 전송 생략: 요약 없음")

    return jsonify({"result": "ok", "count": len(summaries)})

@app.route("/")
def index():
    return "Server is running!"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
