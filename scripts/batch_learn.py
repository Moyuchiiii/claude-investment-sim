"""ウォークフォワード学習の一括実行スクリプト。
複数月のスナップショットを順番に処理し、ルールベースの分析で教訓を自動生成する。
"""
import sys
import json
import argparse
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.repository import LearningLogRepository

SNAPSHOT_DIR = Path(__file__).parent.parent / "learning" / "snapshots"

# 銘柄コード → 日本語名のマッピング
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


def parse_month(month_str: str) -> tuple[int, int]:
    """'YYYY-MM' 形式の文字列を (year, month) のタプルに変換する"""
    parts = month_str.split("-")
    if len(parts) != 2:
        raise ValueError(f"月の形式が不正です: {month_str}（YYYY-MM形式で指定してください）")
    return int(parts[0]), int(parts[1])


def month_range(start: str, end: str) -> list[str]:
    """start から end までの月リストを返す（両端含む）"""
    sy, sm = parse_month(start)
    ey, em = parse_month(end)

    months = []
    y, m = sy, sm
    while (y, m) <= (ey, em):
        months.append(f"{y}-{m:02d}")
        m += 1
        if m > 12:
            m = 1
            y += 1
    return months


def load_snapshots(month_str: str) -> Optional[list[dict]]:
    """スナップショットJSONを読み込む。ファイルが存在しない場合はNoneを返す"""
    path = SNAPSHOT_DIR / f"{month_str}.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_outcomes(month_str: str) -> Optional[list[dict]]:
    """アウトカムJSONを読み込む。ファイルが存在しない場合はNoneを返す"""
    path = SNAPSHOT_DIR / f"{month_str}_outcomes.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_outcome_index(outcomes: list[dict]) -> dict:
    """(date, symbol) をキーにアウトカムの辞書を構築する"""
    index = {}
    for outcome in outcomes:
        key = (outcome["date"], outcome["symbol"])
        index[key] = outcome
    return index


def determine_outcome(return_1m: float) -> str:
    """1ヶ月リターンから WIN / LOSS / HOLD を判定する"""
    if return_1m >= 3.0:
        return "WIN"
    elif return_1m <= -3.0:
        return "LOSS"
    else:
        return "HOLD"


def analyze_rsi(snapshot: dict, outcome: dict) -> Optional[dict]:
    """RSIシグナルとアウトカムを照合して教訓を生成する"""
    indicators = snapshot.get("indicators", {})
    rsi = indicators.get("rsi_14")
    if rsi is None:
        return None

    returns = outcome["returns"]
    ret_1m = returns.get("1m", 0)
    ret_1w = returns.get("1w", 0)

    if rsi < 30:
        # 売られすぎ → 買いシグナル
        result_label = determine_outcome(ret_1m)
        direction = "反発成功" if ret_1m > 0 else "反発失敗（下げ継続）"
        lesson = (
            f"RSI {rsi:.1f}（売られすぎ）で買いシグナル → "
            f"1週間後{ret_1w:+.1f}%、1ヶ月後{ret_1m:+.1f}%。{direction}"
        )
        return {
            "outcome": result_label,
            "lesson": lesson,
            "profit_loss": ret_1m,
            "tags": "indicator:RSI,signal:oversold",
        }
    elif rsi > 70:
        # 買われすぎ → 売りシグナル
        # 売りシグナルなので下落 = WIN
        result_label = determine_outcome(-ret_1m)
        direction = "下落成功（売りシグナル正解）" if ret_1m < 0 else "下落失敗（上昇継続）"
        lesson = (
            f"RSI {rsi:.1f}（買われすぎ）で売りシグナル → "
            f"1週間後{ret_1w:+.1f}%、1ヶ月後{ret_1m:+.1f}%。{direction}"
        )
        return {
            "outcome": result_label,
            "lesson": lesson,
            "profit_loss": -ret_1m,  # 売りシグナルなので符号反転
            "tags": "indicator:RSI,signal:overbought",
        }
    return None


def analyze_macd(snapshot: dict, outcome: dict) -> Optional[dict]:
    """MACDクロスオーバーとアウトカムを照合して教訓を生成する"""
    indicators = snapshot.get("indicators", {})
    macd = indicators.get("macd")
    macd_signal = indicators.get("macd_signal")

    if macd is None or macd_signal is None:
        return None

    returns = outcome["returns"]
    ret_1m = returns.get("1m", 0)
    ret_2w = returns.get("2w", 0)

    # MACDがシグナルラインを上抜け（ゴールデンクロス）
    if macd > macd_signal and macd > 0:
        result_label = determine_outcome(ret_1m)
        direction = "トレンド継続" if ret_1m > 0 else "ダマシ（下落）"
        lesson = (
            f"MACD GC発生（MACD:{macd:.2f} > Signal:{macd_signal:.2f}）→ "
            f"2週間後{ret_2w:+.1f}%、1ヶ月後{ret_1m:+.1f}%。{direction}"
        )
        return {
            "outcome": result_label,
            "lesson": lesson,
            "profit_loss": ret_1m,
            "tags": "indicator:MACD,signal:golden_cross",
        }
    # MACDがシグナルラインを下抜け（デッドクロス）
    elif macd < macd_signal and macd < 0:
        result_label = determine_outcome(-ret_1m)
        direction = "下落継続（売りシグナル正解）" if ret_1m < 0 else "ダマシ（反発）"
        lesson = (
            f"MACD DC発生（MACD:{macd:.2f} < Signal:{macd_signal:.2f}）→ "
            f"2週間後{ret_2w:+.1f}%、1ヶ月後{ret_1m:+.1f}%。{direction}"
        )
        return {
            "outcome": result_label,
            "lesson": lesson,
            "profit_loss": -ret_1m,
            "tags": "indicator:MACD,signal:dead_cross",
        }
    return None


def analyze_bollinger(snapshot: dict, outcome: dict) -> Optional[dict]:
    """ボリンジャーバンドタッチとアウトカムを照合して教訓を生成する"""
    indicators = snapshot.get("indicators", {})
    bb_upper = indicators.get("bb_upper")
    bb_lower = indicators.get("bb_lower")
    current_price = indicators.get("current_price")

    if bb_upper is None or bb_lower is None or current_price is None:
        return None

    returns = outcome["returns"]
    ret_1w = returns.get("1w", 0)
    ret_1m = returns.get("1m", 0)

    # 下限バンドタッチ（買いシグナル）
    if current_price <= bb_lower:
        result_label = determine_outcome(ret_1m)
        direction = "バウンス成功" if ret_1m > 0 else "バウンス失敗（下抜け継続）"
        lesson = (
            f"BB下限タッチ（現値:{current_price:.0f} ≦ 下限:{bb_lower:.0f}）→ "
            f"1週間後{ret_1w:+.1f}%、1ヶ月後{ret_1m:+.1f}%。{direction}"
        )
        return {
            "outcome": result_label,
            "lesson": lesson,
            "profit_loss": ret_1m,
            "tags": "indicator:BB,signal:lower_touch",
        }
    # 上限バンドタッチ（売りシグナル）
    elif current_price >= bb_upper:
        result_label = determine_outcome(-ret_1m)
        direction = "反落成功（売りシグナル正解）" if ret_1m < 0 else "上抜け継続"
        lesson = (
            f"BB上限タッチ（現値:{current_price:.0f} ≧ 上限:{bb_upper:.0f}）→ "
            f"1週間後{ret_1w:+.1f}%、1ヶ月後{ret_1m:+.1f}%。{direction}"
        )
        return {
            "outcome": result_label,
            "lesson": lesson,
            "profit_loss": -ret_1m,
            "tags": "indicator:BB,signal:upper_touch",
        }
    return None


def analyze_adx(snapshot: dict, outcome: dict) -> Optional[dict]:
    """ADX強度とアウトカムを照合して教訓を生成する"""
    indicators = snapshot.get("indicators", {})
    adx = indicators.get("adx_14")
    price_change_5d = indicators.get("price_change_5d")

    if adx is None or price_change_5d is None:
        return None

    # 強いトレンド（ADX > 25）のみ対象
    if adx < 25:
        return None

    returns = outcome["returns"]
    ret_1m = returns.get("1m", 0)

    # 上昇トレンド中の強ADX
    if price_change_5d > 0:
        result_label = determine_outcome(ret_1m)
        direction = "トレンド継続" if ret_1m > 0 else "トレンド転換"
        lesson = (
            f"ADX {adx:.1f}（強い上昇トレンド）→ "
            f"1ヶ月後{ret_1m:+.1f}%。{direction}"
        )
        return {
            "outcome": result_label,
            "lesson": lesson,
            "profit_loss": ret_1m,
            "tags": "indicator:ADX,signal:strong_uptrend",
        }
    # 下落トレンド中の強ADX
    else:
        result_label = determine_outcome(-ret_1m)
        direction = "下落継続" if ret_1m < 0 else "下落トレンド終了"
        lesson = (
            f"ADX {adx:.1f}（強い下落トレンド）→ "
            f"1ヶ月後{ret_1m:+.1f}%。{direction}"
        )
        return {
            "outcome": result_label,
            "lesson": lesson,
            "profit_loss": -ret_1m,
            "tags": "indicator:ADX,signal:strong_downtrend",
        }


def analyze_volume(snapshot: dict, outcome: dict) -> Optional[dict]:
    """出来高異常とアウトカムを照合して教訓を生成する"""
    vol_anomaly = snapshot.get("volume_anomaly", {})
    if not vol_anomaly.get("anomaly", False):
        return None

    vol_ratio = vol_anomaly.get("ratio", 1.0)
    market_data = snapshot.get("market_data", {})
    change_pct = market_data.get("change_pct", 0)

    returns = outcome["returns"]
    ret_1w = returns.get("1w", 0)
    ret_1m = returns.get("1m", 0)

    # 出来高急増 + 上昇 → 強気シグナル
    if change_pct > 0:
        result_label = determine_outcome(ret_1m)
        direction = "上昇継続" if ret_1m > 0 else "急騰後の反落"
        lesson = (
            f"出来高{vol_ratio:.1f}倍の急増＋当日{change_pct:+.1f}%上昇 → "
            f"1週間後{ret_1w:+.1f}%、1ヶ月後{ret_1m:+.1f}%。{direction}"
        )
    else:
        result_label = determine_outcome(-ret_1m)
        direction = "下落継続" if ret_1m < 0 else "急落後の反発"
        lesson = (
            f"出来高{vol_ratio:.1f}倍の急増＋当日{change_pct:+.1f}%下落 → "
            f"1週間後{ret_1w:+.1f}%、1ヶ月後{ret_1m:+.1f}%。{direction}"
        )

    return {
        "outcome": result_label,
        "lesson": lesson,
        "profit_loss": ret_1m if change_pct > 0 else -ret_1m,
        "tags": "indicator:volume,signal:anomaly",
    }


def analyze_fundamentals(snapshot: dict, outcome: dict) -> Optional[dict]:
    """ファンダメンタルズシグナルとアウトカムを照合して教訓を生成する"""
    fundamentals = snapshot.get("fundamentals", {})
    if not fundamentals:
        return None

    per = fundamentals.get("per")
    pbr = fundamentals.get("pbr")
    roe = fundamentals.get("roe")

    returns = outcome["returns"]
    ret_1m = returns.get("1m", 0)

    # 割安 + 高ROEの組み合わせ（バリュー株シグナル）
    signals = []
    if per is not None and per < 15:
        signals.append(f"PER {per:.1f}（割安）")
    if pbr is not None and pbr < 1:
        signals.append(f"PBR {pbr:.2f}（資産割れ）")
    if roe is not None and roe > 0.15:
        signals.append(f"ROE {roe*100:.1f}%（高収益）")

    if len(signals) < 2:
        # シグナルが2つ未満の場合はスキップ
        return None

    result_label = determine_outcome(ret_1m)
    direction = "バリュー投資成功" if ret_1m > 0 else "バリュートラップ"
    signal_str = "・".join(signals)
    lesson = (
        f"ファンダ割安シグナル（{signal_str}）→ "
        f"1ヶ月後{ret_1m:+.1f}%。{direction}"
    )
    return {
        "outcome": result_label,
        "lesson": lesson,
        "profit_loss": ret_1m,
        "tags": "indicator:fundamentals,signal:value",
    }


def analyze_snapshot_pair(snapshot: dict, outcome: dict) -> list[dict]:
    """1つのスナップショットとアウトカムのペアから教訓リストを生成する。
    各テクニカル・ファンダメンタルズ分析器を順番に実行し、シグナルがある教訓のみ返す。
    """
    lessons = []
    analyzers = [
        analyze_rsi,
        analyze_macd,
        analyze_bollinger,
        analyze_adx,
        analyze_volume,
        analyze_fundamentals,
    ]

    for analyzer in analyzers:
        try:
            result = analyzer(snapshot, outcome)
            if result:
                lessons.append(result)
        except Exception as e:
            # 個別アナライザーのエラーはスキップして続行
            pass

    return lessons


def infer_market_context(snapshots: list[dict]) -> str:
    """月全体のスナップショット群から市場コンテキストを推定する。
    騰落率の平均でざっくり相場環境を判定する。
    """
    changes = [
        s["market_data"].get("change_pct", 0)
        for s in snapshots
        if s.get("market_data")
    ]
    if not changes:
        return "unknown"

    avg_change = sum(changes) / len(changes)
    if avg_change > 0.5:
        return "market_up"
    elif avg_change < -0.5:
        return "market_down"
    else:
        return "market_flat"


def process_month(
    month_str: str,
    repo: LearningLogRepository,
    dry_run: bool = False,
) -> int:
    """指定月のスナップショット・アウトカムを処理し、教訓を記録する。
    記録した教訓の件数を返す。
    """
    snapshots = load_snapshots(month_str)
    if snapshots is None:
        print(f"  スキップ: {month_str}.json が見つかりません")
        return 0

    outcomes = load_outcomes(month_str)
    if outcomes is None:
        print(f"  スキップ: {month_str}_outcomes.json が見つかりません")
        return 0

    # (date, symbol) → outcome のインデックスを構築
    outcome_index = build_outcome_index(outcomes)

    # 月全体の市場コンテキストを推定
    market_context = infer_market_context(snapshots)

    recorded_count = 0

    for snapshot in snapshots:
        key = (snapshot["date"], snapshot["symbol"])
        outcome = outcome_index.get(key)
        if outcome is None:
            continue

        lessons = analyze_snapshot_pair(snapshot, outcome)
        symbol = snapshot["symbol"]

        for lesson_data in lessons:
            if dry_run:
                print(
                    f"    [DRY-RUN] {symbol} | {lesson_data['outcome']} | "
                    f"{lesson_data['lesson'][:60]}..."
                )
            else:
                repo.create(
                    trade_id=None,
                    outcome=lesson_data["outcome"],
                    profit_loss=lesson_data.get("profit_loss"),
                    lesson=lesson_data["lesson"],
                    strategy_adjustment=None,
                    tags=lesson_data.get("tags"),
                    symbol=symbol,
                    market_context=market_context,
                )
            recorded_count += 1

    return recorded_count


def main():
    parser = argparse.ArgumentParser(
        description="ウォークフォワード学習の一括実行"
    )
    parser.add_argument(
        "--start",
        required=True,
        metavar="YYYY-MM",
        help="開始月（例: 2018-04）",
    )
    parser.add_argument(
        "--end",
        required=True,
        metavar="YYYY-MM",
        help="終了月（例: 2026-03）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="実際に書き込まず、記録予定の教訓を表示する",
    )
    args = parser.parse_args()

    months = month_range(args.start, args.end)
    repo = LearningLogRepository()

    mode_label = "[DRY-RUN] " if args.dry_run else ""
    print(f"{mode_label}バッチ学習開始: {args.start} 〜 {args.end} ({len(months)}ヶ月)")
    print("-" * 60)

    total_lessons = 0
    skipped_months = 0

    for month_str in months:
        count = process_month(month_str, repo, dry_run=args.dry_run)

        if count == 0:
            skipped_months += 1
        else:
            total_lessons += count
            print(f"Processing {month_str}... {count} lessons recorded")

    print("-" * 60)
    print(f"完了: {len(months) - skipped_months} ヶ月処理、{skipped_months} ヶ月スキップ")
    print(f"合計 {total_lessons} 件の教訓を{'記録予定（dry-run）' if args.dry_run else '記録'}しました")


if __name__ == "__main__":
    main()
