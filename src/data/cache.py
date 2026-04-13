"""データキャッシュ"""
import json
import time
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent.parent / "data" / "cache"


class DataCache:
    """ファイルベースのシンプルなキャッシュ"""

    def __init__(self):
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, category: str, key: str) -> Path:
        """キャッシュファイルのパスを生成"""
        safe_key = key.replace("/", "_").replace("\\", "_").replace(".", "_")
        return CACHE_DIR / f"{category}_{safe_key}.json"

    def get(self, category: str, key: str, max_age_seconds: int) -> dict | None:
        """キャッシュからデータを取得。有効期限切れならNoneを返す"""
        path = self._cache_path(category, key)
        if not path.exists():
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                cached = json.load(f)

            # 有効期限チェック
            cached_at = cached.get("_cached_at", 0)
            if time.time() - cached_at > max_age_seconds:
                return None  # 期限切れ

            return cached.get("data")
        except (json.JSONDecodeError, KeyError):
            return None

    def set(self, category: str, key: str, data) -> None:
        """データをキャッシュに保存"""
        path = self._cache_path(category, key)
        cached = {
            "_cached_at": time.time(),
            "data": data,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cached, f, ensure_ascii=False, indent=2, default=str)

    def clear(self, category: str = None) -> int:
        """キャッシュをクリア。categoryを指定すればそのカテゴリだけ"""
        count = 0
        for path in CACHE_DIR.glob("*.json"):
            if category is None or path.name.startswith(f"{category}_"):
                path.unlink()
                count += 1
        return count
