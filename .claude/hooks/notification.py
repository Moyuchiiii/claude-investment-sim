"""売買通知フック"""
import sys
import json
from datetime import datetime

def main():
    try:
        input_data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    message = input_data.get("message", "")

    # 売買関連の通知をログに記録
    if any(kw in message for kw in ["買い実行", "売り実行", "損切り", "利確"]):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "message": message
        }
        try:
            import pathlib
            log_file = pathlib.Path(__file__).parent.parent.parent / "learning" / "trade_notifications.jsonl"
            log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

    sys.exit(0)

if __name__ == "__main__":
    main()
