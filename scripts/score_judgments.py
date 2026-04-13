"""判断結果のスコアリングと成績追跡"""
import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

SNAPSHOT_DIR = Path(__file__).parent.parent / "learning" / "snapshots"
JUDGMENT_DIR = Path(__file__).parent.parent / "learning" / "judgments"
SCORE_DIR = Path(__file__).parent.parent / "learning" / "scores"

# 正解判定の閾値
THRESHOLD = 3.0  # BUY: +3%以上, SELL: -3%以下, HOLD: ±3%以内


def load_judgments(month_str: str) -> dict:
    """判断ファイルを読み込む"""
    path = JUDGMENT_DIR / f"{month_str}.json"
    if not path.exists():
        print(f"判断ファイルが見つかりません: {path}")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_outcomes(month_str: str) -> list[dict]:
    """アウトカムファイルを読み込む"""
    path = SNAPSHOT_DIR / f"{month_str}_outcomes.json"
    if not path.exists():
        print(f"アウトカムファイルが見つかりません: {path}")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def is_correct(judgment: str, return_1m: float) -> bool:
    """判断が正解かどうか判定"""
    if judgment == "BUY":
        return return_1m >= THRESHOLD
    elif judgment == "SELL":
        return return_1m <= -THRESHOLD
    elif judgment == "HOLD":
        return abs(return_1m) < THRESHOLD
    return False


def score_month(month_str: str) -> dict:
    """指定月の判断をスコアリングする"""
    judgments = load_judgments(month_str)
    outcomes = load_outcomes(month_str)

    # (date, symbol) → outcome のインデックス
    outcome_index = {}
    for o in outcomes:
        key = (o["date"], o["symbol"])
        outcome_index[key] = o

    results = []
    correct = 0
    total = 0
    buy_returns = []
    sell_returns = []

    for j in judgments["judgments"]:
        symbol = j["symbol"]
        date = j["date"]
        judgment = j["judgment"]  # BUY / SELL / HOLD
        reason = j.get("reason", "")

        # 対応するアウトカムを探す
        key = (date, symbol)
        outcome = outcome_index.get(key)
        if outcome is None:
            continue

        return_1m = outcome["returns"]["1m"]
        return_1w = outcome["returns"].get("1w", 0)
        max_dd = outcome.get("max_drawdown_pct", 0)

        hit = is_correct(judgment, return_1m)
        if hit:
            correct += 1
        total += 1

        if judgment == "BUY":
            buy_returns.append(return_1m)
        elif judgment == "SELL":
            sell_returns.append(-return_1m)  # 売りなので符号反転

        results.append({
            "symbol": symbol,
            "symbol_name": outcome.get("symbol_name", symbol),
            "date": date,
            "judgment": judgment,
            "reason": reason,
            "return_1w": return_1w,
            "return_1m": return_1m,
            "max_drawdown": max_dd,
            "correct": hit,
        })

    accuracy = correct / total if total > 0 else 0

    # 期待値計算: BUY判断した銘柄の平均リターン
    avg_buy_return = sum(buy_returns) / len(buy_returns) if buy_returns else 0
    avg_sell_return = sum(sell_returns) / len(sell_returns) if sell_returns else 0

    # BUY/SELL/HOLDの内訳
    buy_count = sum(1 for r in results if r["judgment"] == "BUY")
    sell_count = sum(1 for r in results if r["judgment"] == "SELL")
    hold_count = sum(1 for r in results if r["judgment"] == "HOLD")

    buy_correct = sum(1 for r in results if r["judgment"] == "BUY" and r["correct"])
    sell_correct = sum(1 for r in results if r["judgment"] == "SELL" and r["correct"])
    hold_correct = sum(1 for r in results if r["judgment"] == "HOLD" and r["correct"])

    score = {
        "month": month_str,
        "total": total,
        "correct": correct,
        "accuracy": round(accuracy * 100, 1),
        "breakdown": {
            "BUY": {"total": buy_count, "correct": buy_correct,
                     "accuracy": round(buy_correct / buy_count * 100, 1) if buy_count > 0 else 0},
            "SELL": {"total": sell_count, "correct": sell_correct,
                     "accuracy": round(sell_correct / sell_count * 100, 1) if sell_count > 0 else 0},
            "HOLD": {"total": hold_count, "correct": hold_correct,
                     "accuracy": round(hold_correct / hold_count * 100, 1) if hold_count > 0 else 0},
        },
        "expected_value": {
            "avg_buy_return": round(avg_buy_return, 2),
            "avg_sell_return": round(avg_sell_return, 2),
        },
        "details": results,
    }

    return score


def print_score(score: dict):
    """スコアをきれいに表示"""
    print(f"\n{'='*60}")
    print(f"  {score['month']} スコアリング結果")
    print(f"{'='*60}")
    print(f"\n  正解率: {score['correct']}/{score['total']} = {score['accuracy']}%")
    print(f"\n  内訳:")
    for j_type in ["BUY", "SELL", "HOLD"]:
        b = score["breakdown"][j_type]
        print(f"    {j_type}: {b['correct']}/{b['total']} ({b['accuracy']}%)")
    print(f"\n  期待値:")
    print(f"    BUY判断の平均リターン: {score['expected_value']['avg_buy_return']:+.2f}%")
    print(f"    SELL判断の平均リターン: {score['expected_value']['avg_sell_return']:+.2f}%")

    # 不正解リスト
    misses = [r for r in score["details"] if not r["correct"]]
    if misses:
        print(f"\n  不正解 ({len(misses)}件):")
        for m in misses:
            print(f"    {m['symbol']} ({m['symbol_name']}): "
                  f"{m['judgment']} → 実際{m['return_1m']:+.1f}% "
                  f"| 理由: {m['reason'][:50]}")
    print()


def load_all_scores() -> list[dict]:
    """全月のスコアを読み込んで正解率の推移を表示"""
    if not SCORE_DIR.exists():
        return []

    scores = []
    for f in sorted(SCORE_DIR.glob("*.json")):
        with open(f, encoding="utf-8") as fh:
            scores.append(json.load(fh))
    return scores


def print_progress(scores: list[dict]):
    """月別の正解率推移を表示"""
    if not scores:
        print("まだスコアがありません")
        return

    print(f"\n{'='*60}")
    print(f"  正解率の推移")
    print(f"{'='*60}")
    print(f"  {'月':10s} {'正解率':>8s} {'BUY':>8s} {'SELL':>8s} {'HOLD':>8s} {'BUY期待値':>10s}")
    print(f"  {'-'*54}")

    for s in scores:
        b = s["breakdown"]
        ev = s["expected_value"]
        print(f"  {s['month']:10s} {s['accuracy']:>7.1f}% "
              f"{b['BUY']['accuracy']:>7.1f}% "
              f"{b['SELL']['accuracy']:>7.1f}% "
              f"{b['HOLD']['accuracy']:>7.1f}% "
              f"{ev['avg_buy_return']:>+9.2f}%")

    # 平均
    avg_acc = sum(s["accuracy"] for s in scores) / len(scores)
    print(f"  {'-'*54}")
    print(f"  {'平均':10s} {avg_acc:>7.1f}%")

    # トレンド（前半 vs 後半）
    if len(scores) >= 4:
        half = len(scores) // 2
        first_half = sum(s["accuracy"] for s in scores[:half]) / half
        second_half = sum(s["accuracy"] for s in scores[half:]) / (len(scores) - half)
        diff = second_half - first_half
        trend = "↑ 改善" if diff > 0 else "↓ 悪化" if diff < 0 else "→ 横ばい"
        print(f"\n  前半平均: {first_half:.1f}% → 後半平均: {second_half:.1f}% ({diff:+.1f}% {trend})")
    print()


def main():
    parser = argparse.ArgumentParser(description="判断のスコアリング")
    parser.add_argument("month", nargs="?", help="スコアリングする月（YYYY-MM）")
    parser.add_argument("--progress", action="store_true", help="正解率の推移を表示")
    args = parser.parse_args()

    if args.progress:
        scores = load_all_scores()
        print_progress(scores)
        return

    if not args.month:
        print("月を指定してください（例: 2025-01）または --progress で推移表示")
        return

    score = score_month(args.month)
    print_score(score)

    # スコアを保存
    SCORE_DIR.mkdir(parents=True, exist_ok=True)
    score_path = SCORE_DIR / f"{args.month}.json"
    with open(score_path, "w", encoding="utf-8") as f:
        json.dump(score, f, ensure_ascii=False, indent=2)
    print(f"  スコア保存: {score_path}")


if __name__ == "__main__":
    main()
