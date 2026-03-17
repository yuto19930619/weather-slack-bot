import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

# .envファイルがあれば読み込む
load_dotenv()

# 設定
AREA_CODE = os.environ.get("AREA_CODE", "080000") # 茨城県
AREA_NAME = os.environ.get("AREA_NAME", "中央")    # 水戸市を含む中央
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

def get_weather_forecast():
    """気象庁APIから天気予報を取得する"""
    url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{AREA_CODE}.json"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        # timeSeries[0] = 天気, timeSeries[1] = 降水確率
        weather_areas = data[0]["timeSeries"][0]["areas"]
        target_weather_area = next((area for area in weather_areas if area["area"]["name"] == AREA_NAME), None)
        
        pop_areas = data[0]["timeSeries"][1]["areas"]
        target_pop_area = next((area for area in pop_areas if area["area"]["name"] == AREA_NAME), None)

        if not target_weather_area or not target_pop_area:
            return None

        # --- ここから明日の予報に特化 ---

        # 明日の天気 (インデックス[1]が明日)
        tomorrow_weather = target_weather_area["weathers"][1].replace("　", " ").strip()

        # 明日の降水確率 
        # 気象庁APIは今日・明日の降水確率が1つの配列に入っているため、後ろから4つ（明日分）を取得
        all_pops = target_pop_area["pops"]
        tomorrow_pops = all_pops[-4:] 
        pop_text = " / ".join(tomorrow_pops) + " %"

        # 洗濯判定 (明日の天気と降水確率で判定)
        is_laundry_day = True
        if "雨" in tomorrow_weather or "雪" in tomorrow_weather:
            is_laundry_day = False
        if any(int(p) >= 40 for p in tomorrow_pops if p.isdigit()):
            is_laundry_day = False
            
        laundry_status = "明日は外干し日和です！👕☀️" if is_laundry_day else "明日は部屋干しが無難かもしれません🌂"

        return {
            "area": AREA_NAME,
            "weather": tomorrow_weather,
            "pops": pop_text,
            "laundry_status": laundry_status
        }
    except Exception as e:
        print(f"天気予報の取得に失敗しました: {e}")
        return None

def format_slack_message(forecast):
    """取得した予報をSlackのメッセージフォーマットにする"""
    # 明日の日付を計算
    tomorrow_date = (datetime.now() + timedelta(days=1)).strftime("%Y年%m月%d日")
    
    text = (
        f"*{tomorrow_date} 茨城県（{forecast['area']}）の天気予報*\n\n"
        f"🌦️ *明日の天気*: {forecast['weather']}\n"
        f"☔ *降水確率*: {forecast['pops']}\n\n"
        f"👕 *洗濯アドバイス*: {forecast['laundry_status']}"
    )
    return {"text": text}

def post_to_slack(message):
    """Slackにメッセージを送信する"""
    if not SLACK_WEBHOOK_URL or SLACK_WEBHOOK_URL == "your_webhook_url_here":
        print("※ Slack Webhook URLが未設定のため、実際のSlack通知はスキップします。\n")
        print("--- Slackへの送信予定メッセージ ---")
        print(message["text"])
        print("-----------------------------------")
        return

    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=message)
        response.raise_for_status()
        print("Slackへの通知が完了しました。")
    except Exception as e:
        print(f"Slackへの通知に失敗しました: {e}")

if __name__ == "__main__":
    forecast = get_weather_forecast()
    if forecast:
        message = format_slack_message(forecast)
        post_to_slack(message)
    else:
        print("天気データの抽出に失敗したため、通知をスキップしました。")
