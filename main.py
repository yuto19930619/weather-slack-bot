import os
import requests
from datetime import datetime
from dotenv import load_dotenv

# .envファイルがあれば読み込む
load_dotenv()

# 設定
AREA_CODE = os.environ.get("AREA_CODE", "080000") # 茨城県
AREA_NAME = os.environ.get("AREA_NAME", "中央")   # 水戸市を含む中央
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

        # 今日の天気 (0番目が今日)
        today_weather = target_weather_area["weathers"][0]
        # 前後の全角スペースなどを整理
        today_weather = today_weather.replace("　", " ").strip()

        # 今日の降水確率 (6時間ごと)
        pops = target_pop_area["pops"]
        
        # JMA APIは時間が過ぎるとpopsの配列要素数が減る場合があるため、表示用に結合
        pop_text = " / ".join(pops) + " %"

        # 洗濯判定 (簡易アルゴリズム)
        # 雨や雪の文字が含まれているか、降水確率のいずれかが40%以上なら注意
        is_laundry_day = True
        if "雨" in today_weather or "雪" in today_weather:
            is_laundry_day = False
        if any(int(p) >= 40 for p in pops if p.isdigit()):
            is_laundry_day = False
            
        laundry_status = "外干し日和です！👕☀️" if is_laundry_day else "部屋干しが無難かもしれません🌂"

        return {
            "area": AREA_NAME,
            "weather": today_weather,
            "pops": pop_text,
            "laundry_status": laundry_status
        }
    except Exception as e:
        print(f"天気予報の取得に失敗しました: {e}")
        return None

def format_slack_message(forecast):
    """取得した予報をSlackのメッセージフォーマットにする"""
    date_str = datetime.now().strftime("%Y年%m月%d日")
    text = (
        f"*{date_str} 茨城県（{forecast['area']}）の天気予報*\n\n"
        f"🌦️ *今日の天気*: {forecast['weather']}\n"
        f"☔ *降水確率*: {forecast['pops']}\n\n"
        f"👕 *洗濯アドバイス*: {forecast['laundry_status']}"
    )
    return {
        "text": text
    }

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
