# claude-investment-sim

Claude Codeによる自律投資シミュレーター。仮想マネーで株式売買を行い、強化学習的に判断精度を向上させる。

## 基本方針
- 日本語で応答する
- コードのコメントは日本語（変数名・関数名は英語）
- テストを先に書く（TDD）
- 実際のリアルマネーは使わない。すべて仮想マネー

## よく使うコマンド
```bash
# DB初期化
python scripts/setup_db.py

# 売買サイクル実行
python scripts/run_trading.py

# バックテスト
python scripts/backtest.py

# ダッシュボード起動
streamlit run src/dashboard/app.py

# テスト実行
pytest tests/ -v
```

## アーキテクチャ
- src/data/: 株価データ取得・テクニカル指標計算
- src/engine/: ポートフォリオ管理・売買実行・リスク管理
- src/ai/: Claude Code CLIで売買判断・学習
- src/db/: SQLiteデータベース操作
- src/dashboard/: Streamlitダッシュボード
- scripts/: 実行スクリプト
- learning/: 売買日誌・戦略進化記録

## コミット規約
- 日本語でコミットメッセージを書く
- 形式: `<種別>: <概要>`
