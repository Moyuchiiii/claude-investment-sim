"""
/trade スケジュール管理スクリプト

使い方:
  python scripts/trade_scheduler.py status   # 最終実行・次回推奨時刻を表示
  python scripts/trade_scheduler.py history  # 実行履歴を表示
  python scripts/trade_scheduler.py record   # /trade 実行を記録
"""

import sys
import io
import json
import argparse
from pathlib import Path
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

# Windows環境でのUTF-8出力を強制する
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# プロジェクトルートへのパス解決
ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"
SCHEDULE_FILE = DATA_DIR / "schedule.json"

# 東証タイムゾーン（JST）
JST = ZoneInfo("Asia/Tokyo")

# 取引推奨時刻（後場終了後）
RECOMMENDED_HOUR = 15
RECOMMENDED_MINUTE = 30


def load_schedule() -> dict:
    """schedule.json を読み込む。存在しない場合は空の初期値を返す"""
    if not SCHEDULE_FILE.exists():
        return {
            "last_execution": None,
            "executions": []
        }
    with open(SCHEDULE_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_schedule(data: dict) -> None:
    """schedule.json に書き込む"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def is_weekday(d: date) -> bool:
    """平日かどうかを判定する（土日は False）"""
    return d.weekday() < 5  # 0=月曜 ... 4=金曜


def next_weekday(d: date) -> date:
    """翌営業日を返す（土曜 → 月曜、日曜 → 月曜）"""
    d = d + timedelta(days=1)
    while not is_weekday(d):
        d = d + timedelta(days=1)
    return d


def calc_next_recommended(last_exec_str: str | None) -> datetime:
    """
    次回推奨実行日時を計算する

    ロジック:
    - 今日すでに実行済み → 翌営業日 15:30
    - 今が平日15:30以降 → 今日の 15:30（推奨ウィンドウ内）
    - 今が平日 15:30 前 → 今日の 15:30
    - 土日 → 翌月曜 15:30
    """
    now = datetime.now(JST)
    today = now.date()

    # 今日すでに実行済みかチェック
    ran_today = False
    if last_exec_str:
        last_exec = datetime.fromisoformat(last_exec_str)
        if last_exec.date() == today:
            ran_today = True

    def make_recommended(d: date) -> datetime:
        return datetime(
            d.year, d.month, d.day,
            RECOMMENDED_HOUR, RECOMMENDED_MINUTE,
            tzinfo=JST
        )

    if ran_today:
        # 今日は終わり、翌営業日へ
        return make_recommended(next_weekday(today))

    if not is_weekday(today):
        # 土日は翌月曜
        return make_recommended(next_weekday(today))

    # 平日: 15:30以降であれば「今日推奨ウィンドウ内」だが、
    # 次に"/trade"を実行すべき時刻としては翌日を案内
    recommended_today = make_recommended(today)
    if now >= recommended_today:
        # 推奨ウィンドウを過ぎているなら翌営業日
        return make_recommended(next_weekday(today))

    # 今日の15:30前
    return recommended_today


def format_datetime(dt: datetime | None) -> str:
    """datetime を見やすい文字列にフォーマットする"""
    if dt is None:
        return "未実行"
    weekdays_ja = ["月", "火", "水", "木", "金", "土", "日"]
    wd = weekdays_ja[dt.weekday()]
    return dt.strftime(f"%Y-%m-%d({wd}) %H:%M")


def calc_streak(executions: list[dict]) -> int:
    """連続実行日数（ストリーク）を計算する"""
    if not executions:
        return 0

    # 日付のセットを作成（最新順）
    executed_dates = sorted(
        {datetime.fromisoformat(e["timestamp"]).date() for e in executions},
        reverse=True
    )

    today = datetime.now(JST).date()
    streak = 0
    expected = today

    for d in executed_dates:
        # 今日または連続する前日を確認
        if d == expected or (streak == 0 and d == today - timedelta(days=1)):
            if streak == 0 and d < today:
                expected = d
            streak += 1
            expected -= timedelta(days=1)
            # 週末をスキップ
            while not is_weekday(expected):
                expected -= timedelta(days=1)
        else:
            break

    return streak


def cmd_status() -> None:
    """最終実行時刻・次回推奨時刻・ストリークを表示する"""
    data = load_schedule()
    last_exec_str = data.get("last_execution")
    executions = data.get("executions", [])

    last_exec_dt = None
    if last_exec_str:
        last_exec_dt = datetime.fromisoformat(last_exec_str)

    next_dt = calc_next_recommended(last_exec_str)
    streak = calc_streak(executions)

    now = datetime.now(JST)

    print("=" * 50)
    print("  /trade スケジュール状況")
    print("=" * 50)
    print(f"  現在時刻    : {format_datetime(now)}")
    print(f"  最終実行    : {format_datetime(last_exec_dt)}")
    print(f"  次回推奨    : {format_datetime(next_dt)}")
    print(f"  連続実行    : {streak} 日")
    print(f"  総実行回数  : {len(executions)} 回")
    print("=" * 50)

    # 次回まで何時間か表示
    if next_dt > now:
        delta = next_dt - now
        hours = int(delta.total_seconds() // 3600)
        minutes = int((delta.total_seconds() % 3600) // 60)
        print(f"  あと {hours}時間{minutes}分 で推奨時刻")
    else:
        print("  [!] 推奨時刻を過ぎています — /trade を実行してください")
    print("=" * 50)

    # JSON形式でも出力（ダッシュボード連携用）
    result = {
        "last_execution": last_exec_str,
        "next_recommended": next_dt.isoformat(),
        "streak": streak,
        "total_executions": len(executions),
        "overdue": now >= next_dt
    }
    print("\n--- JSON (ダッシュボード用) ---")
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_history() -> None:
    """実行履歴を新しい順に表示する"""
    data = load_schedule()
    executions = data.get("executions", [])

    if not executions:
        print("実行履歴なし")
        return

    # 新しい順にソート
    sorted_execs = sorted(executions, key=lambda e: e["timestamp"], reverse=True)

    print("=" * 60)
    print("  /trade 実行履歴")
    print("=" * 60)
    print(f"  {'日時':<25}  {'取引件数':>6}  {'ポートフォリオ':>14}")
    print("-" * 60)

    for e in sorted_execs[:20]:  # 最新20件まで表示
        dt = datetime.fromisoformat(e["timestamp"])
        trades = e.get("trades_made", "-")
        pv = e.get("portfolio_value")
        pv_str = f"¥{pv:,.0f}" if pv else "不明"
        trades_str = f"{trades}件" if isinstance(trades, int) else str(trades)
        print(f"  {format_datetime(dt):<25}  {trades_str:>6}  {pv_str:>14}")

    print("=" * 60)
    print(f"  合計 {len(executions)} 件")


def cmd_record(trades_made: int | None = None, portfolio_value: float | None = None) -> None:
    """
    /trade の実行を記録する

    SKILL.md から自動呼び出しされるコマンド。
    trades_made と portfolio_value はオプションで渡せる。
    """
    data = load_schedule()
    now = datetime.now(JST)
    now_iso = now.isoformat()

    # 実行記録を追加
    record = {
        "timestamp": now_iso,
        "trades_made": trades_made,
        "portfolio_value": portfolio_value
    }
    data["executions"].append(record)
    data["last_execution"] = now_iso

    save_schedule(data)

    streak = calc_streak(data["executions"])
    print(f"[OK] /trade 実行を記録しました")
    print(f"   日時: {format_datetime(now)}")
    print(f"   連続実行: {streak} 日")
    if trades_made is not None:
        print(f"   取引件数: {trades_made}")
    if portfolio_value is not None:
        print(f"   ポートフォリオ: ¥{portfolio_value:,.0f}")


def main():
    parser = argparse.ArgumentParser(
        description="/trade スケジュール管理ツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
コマンド:
  status   最終実行・次回推奨時刻・ストリークを表示
  history  実行履歴を表示（最新20件）
  record   /trade 実行を記録する

オプション（record コマンド専用）:
  --trades <int>     実行した取引件数
  --value <float>    記録時点のポートフォリオ評価額
        """
    )
    parser.add_argument(
        "command",
        choices=["status", "history", "record"],
        help="実行するコマンド"
    )
    parser.add_argument(
        "--trades",
        type=int,
        default=None,
        help="取引件数（record コマンド用）"
    )
    parser.add_argument(
        "--value",
        type=float,
        default=None,
        help="ポートフォリオ評価額（record コマンド用）"
    )

    args = parser.parse_args()

    if args.command == "status":
        cmd_status()
    elif args.command == "history":
        cmd_history()
    elif args.command == "record":
        cmd_record(trades_made=args.trades, portfolio_value=args.value)


if __name__ == "__main__":
    main()
