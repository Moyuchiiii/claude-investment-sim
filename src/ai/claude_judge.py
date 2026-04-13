"""Claude Code CLIで売買判断を実行"""
import subprocess
import json
import yaml
from pathlib import Path
from typing import Optional

CONFIG_PATH = Path(__file__).parent.parent.parent / "config.yaml"

def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)

class ClaudeJudge:
    """Claude Code CLI を使って投資判断を行う"""

    def __init__(self):
        self.config = load_config()
        self.claude_config = self.config["claude"]

    def judge(self, prompt: str) -> Optional[dict]:
        """Claude CLIでプロンプトを実行し、JSON結果を取得"""
        try:
            result = subprocess.run(
                [
                    "claude", "-p", prompt,
                    "--output-format", "json",
                    "--model", self.claude_config.get("model", "sonnet"),
                ],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(Path(__file__).parent.parent.parent)
            )

            if result.returncode != 0:
                print(f"Claude CLI エラー: {result.stderr}")
                return None

            # claude --output-format json はメタデータ付きJSONを返す
            # resultフィールドにテキストが入る
            response = json.loads(result.stdout)
            response_text = response.get("result", result.stdout)

            # レスポンスからJSONを抽出
            return self._extract_json(response_text)

        except subprocess.TimeoutExpired:
            print("Claude CLI タイムアウト（120秒）")
            return None
        except Exception as e:
            print(f"Claude CLI 実行エラー: {e}")
            return None

    def _extract_json(self, text: str) -> Optional[dict]:
        """テキストからJSON部分を抽出"""
        # まず全体をJSONとしてパース
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            pass

        # ```json ... ``` ブロックを探す
        if "```json" in str(text):
            try:
                json_str = str(text).split("```json")[1].split("```")[0].strip()
                return json.loads(json_str)
            except (IndexError, json.JSONDecodeError):
                pass

        # { ... } を探す
        text_str = str(text)
        start = text_str.find("{")
        end = text_str.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text_str[start:end])
            except json.JSONDecodeError:
                pass

        return None
