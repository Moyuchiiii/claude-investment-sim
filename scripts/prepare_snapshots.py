"""過去データの週次スナップショットを生成"""
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

import yfinance as yf
import yaml
from src.data.indicators import TechnicalIndicators

CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"
SNAPSHOT_DIR = Path(__file__).parent.parent / "learning" / "snapshots"

SYMBOL_NAMES = {
    "7203.T": "トヨタ自動車", "6758.T": "ソニーG", "9984.T": "ソフトバンクG",
    "6861.T": "キーエンス", "8306.T": "三菱UFJ", "6501.T": "日立製作所",
    "7974.T": "任天堂", "4063.T": "信越化学", "9432.T": "NTT", "6902.T": "デンソー",
    "4502.T": "武田薬品工業", "4568.T": "第一三共", "8801.T": "三井不動産",
    "8802.T": "三菱地所", "9983.T": "ファーストリテイリング", "3382.T": "セブン＆アイHD",
    "2502.T": "アサヒグループHD", "2503.T": "キリンHD", "9020.T": "JR東日本",
    "9022.T": "JR東海", "1812.T": "鹿島建設", "8766.T": "東京海上HD",
    "8058.T": "三菱商事", "8001.T": "伊藤忠商事", "8035.T": "東京エレクトロン",
    "6367.T": "ダイキン工業", "8316.T": "三井住友FG",
}


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_all_symbols():
    config = load_config()
    symbols = []
    for market in config["markets"].values():
        if market.get("enabled"):
            symbols.extend(market["symbols"])
    return symbols


def generate_monthly_snapshots(year: int, month: int):
    """指定月の週次スナップショットを生成"""
    symbols = get_all_symbols()
    indicators = TechnicalIndicators()

    # 月の開始日と終了日
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = datetime(year, month + 1, 1) - timedelta(days=1)

    # 十分な過去データを取得するために、3ヶ月前から取得
    fetch_start = start_date - timedelta(days=90)

    month_str = f"{year}-{month:02d}"
    snapshots = []

    print(f"=== {month_str} のスナップショットを生成中 ===")

    for symbol in symbols:
        print(f"  {symbol} ({SYMBOL_NAMES.get(symbol, '')}) ...", end=" ")

        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(start=fetch_start.strftime("%Y-%m-%d"),
                                  end=(end_date + timedelta(days=1)).strftime("%Y-%m-%d"))

            if hist.empty or len(hist) < 30:
                print("データ不足、スキップ")
                continue

            # 月内の金曜日（または最終営業日）を週次ポイントとして抽出
            month_data = hist[hist.index >= start_date.strftime("%Y-%m-%d")]
            month_data = month_data[month_data.index <= end_date.strftime("%Y-%m-%d")]

            if month_data.empty:
                print("月内データなし、スキップ")
                continue

            # 週ごとにリサンプル（金曜日基準）
            weekly_dates = month_data.resample("W-FRI").last().dropna(subset=["Close"]).index

            for date in weekly_dates:
                # この日時点までのデータでテクニカル指標を計算
                data_until = hist[hist.index <= date]
                if len(data_until) < 30:
                    continue

                tech = indicators.calculate_all(data_until)
                signals = indicators.get_signals(tech) if "error" not in tech else []

                # この日の市場データ
                current = data_until.iloc[-1]
                prev = data_until.iloc[-2] if len(data_until) > 1 else current

                # 出来高異常チェック
                avg_vol = float(data_until["Volume"].tail(21).iloc[:-1].mean()) if len(data_until) > 21 else float(data_until["Volume"].mean())
                current_vol = float(current["Volume"])
                vol_ratio = current_vol / avg_vol if avg_vol > 0 else 1.0

                snapshot = {
                    "date": str(date.date()),
                    "symbol": symbol,
                    "symbol_name": SYMBOL_NAMES.get(symbol, symbol),
                    "market_data": {
                        "open": float(current["Open"]),
                        "high": float(current["High"]),
                        "low": float(current["Low"]),
                        "close": float(current["Close"]),
                        "volume": int(current["Volume"]),
                        "prev_close": float(prev["Close"]),
                        "change_pct": round((float(current["Close"]) / float(prev["Close"]) - 1) * 100, 2),
                    },
                    "indicators": {k: (float(v) if v is not None and not isinstance(v, str) else v)
                                   for k, v in tech.items()} if "error" not in tech else {},
                    "signals": signals,
                    "volume_anomaly": {
                        "ratio": round(vol_ratio, 2),
                        "anomaly": vol_ratio >= 2.0,
                    },
                }
                snapshots.append(snapshot)

            print(f"{len([s for s in snapshots if s['symbol'] == symbol])} 週分")

        except Exception as e:
            print(f"エラー: {e}")
            continue

    # 保存
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = SNAPSHOT_DIR / f"{month_str}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(snapshots, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n保存: {output_path} ({len(snapshots)} スナップショット)")
    return output_path


def generate_outcome(year: int, month: int):
    """指定月の翌月における結果（答え合わせ用）を生成"""
    # スナップショットを読み込む
    month_str = f"{year}-{month:02d}"
    snapshot_path = SNAPSHOT_DIR / f"{month_str}.json"

    if not snapshot_path.exists():
        print(f"スナップショットが見つかりません: {snapshot_path}")
        return None

    with open(snapshot_path, "r", encoding="utf-8") as f:
        snapshots = json.load(f)

    # 翌月の期間
    if month == 12:
        next_month_start = datetime(year + 1, 1, 1)
        next_month_end = datetime(year + 1, 1, 31)
    else:
        next_month_start = datetime(year, month + 1, 1)
        if month + 1 == 12:
            next_month_end = datetime(year, 12, 31)
        else:
            next_month_end = datetime(year, month + 2, 1) - timedelta(days=1)

    print(f"=== {month_str} の答え合わせデータを生成中 ===")
    print(f"  判定期間: {next_month_start.date()} 〜 {next_month_end.date()}")

    outcomes = []

    for snap in snapshots:
        symbol = snap["symbol"]
        snap_date = snap["date"]

        try:
            ticker = yf.Ticker(symbol)
            # スナップショット日から翌月末までのデータ
            hist = ticker.history(start=snap_date,
                                  end=(next_month_end + timedelta(days=1)).strftime("%Y-%m-%d"))

            if hist.empty or len(hist) < 2:
                continue

            entry_price = snap["market_data"]["close"]

            # 1週間後
            week_later = hist.iloc[min(5, len(hist) - 1)]
            week_return = (float(week_later["Close"]) / entry_price - 1) * 100

            # 2週間後
            two_week_later = hist.iloc[min(10, len(hist) - 1)]
            two_week_return = (float(two_week_later["Close"]) / entry_price - 1) * 100

            # 1ヶ月後
            month_later = hist.iloc[min(20, len(hist) - 1)]
            month_return = (float(month_later["Close"]) / entry_price - 1) * 100

            # 最大ドローダウン（期間中）
            closes = hist["Close"].values
            peak = closes[0]
            max_dd = 0
            for c in closes:
                if c > peak:
                    peak = c
                dd = (c - peak) / peak * 100
                if dd < max_dd:
                    max_dd = dd

            # 最大上昇
            max_gain = (max(closes) / entry_price - 1) * 100

            outcome = {
                "date": snap_date,
                "symbol": symbol,
                "symbol_name": snap["symbol_name"],
                "entry_price": entry_price,
                "returns": {
                    "1w": round(week_return, 2),
                    "2w": round(two_week_return, 2),
                    "1m": round(month_return, 2),
                },
                "max_drawdown_pct": round(max_dd, 2),
                "max_gain_pct": round(max_gain, 2),
                "signals_at_entry": snap["signals"],
                "indicators_at_entry": snap["indicators"],
            }
            outcomes.append(outcome)

        except Exception as e:
            continue

    # 保存
    output_path = SNAPSHOT_DIR / f"{month_str}_outcomes.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(outcomes, f, ensure_ascii=False, indent=2, default=str)

    print(f"保存: {output_path} ({len(outcomes)} 件)")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="過去データのスナップショット生成")
    parser.add_argument("--year", type=int, required=True, help="年 (例: 2025)")
    parser.add_argument("--month", type=int, required=True, help="月 (例: 4)")
    parser.add_argument("--outcomes", action="store_true", help="答え合わせデータも生成")
    parser.add_argument("--range", type=int, default=1, help="何ヶ月分生成するか (例: 6)")
    args = parser.parse_args()

    for i in range(args.range):
        m = args.month + i
        y = args.year
        while m > 12:
            m -= 12
            y += 1

        generate_monthly_snapshots(y, m)

        if args.outcomes:
            generate_outcome(y, m)


if __name__ == "__main__":
    main()
