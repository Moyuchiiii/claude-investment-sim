# claude-investment-sim

Claude Codeによる自律投資シミュレーター。

## セットアップ

```bash
git clone <repo-url>
cd claude-investment-sim
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python scripts/setup_db.py
```

## 使い方

```bash
# 売買サイクル実行
python scripts/run_trading.py

# ダッシュボード
streamlit run src/dashboard/app.py

# テスト
pytest tests/ -v
```
