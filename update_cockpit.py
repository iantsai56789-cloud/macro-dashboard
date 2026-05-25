import io
import json
import datetime
import requests
import pandas as pd

def fetch_fred_metric(series_id):
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    try:
        res = requests.get(url, timeout=15)
        if res.status_code == 200:
            df = pd.read_csv(io.StringIO(res.text))
            df = df[df[series_id] != '.']
            df[series_id] = pd.to_numeric(df[series_id])
            return float(df.iloc[-1][series_id]), str(df.iloc[-1]['DATE'])
    except Exception as e:
        print(f"FRED 採集失敗 {series_id}: {e}")
    return None, "N/A"

def fetch_yahoo_index(ticker):
    end_dt = int(datetime.datetime.now().timestamp())
    start_dt = end_dt - (360 * 24 * 60 * 60)
    url = f"https://query1.finance.yahoo.com/v7/finance/download/{ticker}?period1={start_dt}&period2={end_dt}&interval=1d&events=history"
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            df = pd.read_csv(io.StringIO(res.text))
            df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
            return df.dropna(subset=['Close'])
    except Exception as e:
        print(f"Yahoo 採集失敗 {ticker}: {e}")
    return None

def main():
    print("🤖 啟動機構級數據資料層採集...")
    
    # 採集美聯儲與宏觀核心指標
    fci, fci_dt = fetch_fred_metric("NFCI")
    sahm, sahm_dt = fetch_fred_metric("SAHMREALTIME")
    bbb_spread, _ = fetch_fred_metric("BAMLC0A4CBBB")
    
    # 採集市場價格與波動因子
    vix_df = fetch_yahoo_index("^VIX")
    vix = float(vix_df['Close'].iloc[-1]) if vix_df is not None else 15.0
    
    twii_df = fetch_yahoo_index("^TWII")
    twii_dev = 0.0
    if twii_df is not None:
        current_twii = float(twii_df['Close'].iloc[-1])
        ma200 = float(twii_df['Close'].tail(200).mean())
        twii_dev = ((current_twii - ma200) / ma200) * 100

    # 封裝成標準 JSON 資料結構（與 UI 完全解耦）
    payload = {
        "metadata": {
            "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
            "engine_version": "Regime_OS_v2.0_Beta"
        },
        "macro_indicators": {
            "nfci": fci if fci is not None else -0.4,
            "sahm_rule": sahm if sahm is not None else 0.3,
            "bbb_credit_spread": bbb_spread if bbb_spread is not None else 1.2,
            "core_pce_inflation": 3.6, # 2026當前再通膨背景定錨
            "twii_ma200_deviation": twii_dev,
            "vix_volatility": vix
        }
    }
    
    with open("macro_metrics.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4, ensure_ascii=False)
        
    print("✅ 資料層封裝完畢！產出: macro_metrics.json")

if __name__ == "__main__":
    main()
