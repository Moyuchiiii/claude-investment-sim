"""売買実行時の安全チェックフック"""
import sys
import json

def main():
    # stdinからツール呼び出し情報を読む
    try:
        input_data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Bashコマンドの場合のみチェック
    if tool_name != "Bash":
        sys.exit(0)

    command = tool_input.get("command", "")

    # 危険なコマンドをブロック
    dangerous_patterns = [
        "rm -rf",
        "rm -r /",
        "DROP TABLE",
        "DELETE FROM portfolio",
        "DELETE FROM trades",
        "DELETE FROM performance",
        "git reset --hard",
    ]

    for pattern in dangerous_patterns:
        if pattern.lower() in command.lower():
            print(json.dumps({
                "decision": "block",
                "reason": f"危険なコマンドをブロック: {pattern}"
            }))
            sys.exit(2)

    sys.exit(0)

if __name__ == "__main__":
    main()
