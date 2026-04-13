# Claude Investment Simulator

Claude Codeが自律的に日本株の売買判断を行う投資シミュレーター。
仮想資金100万円でスタートし、テクニカル分析をもとにClaude自身がトレーダーとして判断・実行する。

## 特徴

- Claude Codeのスキル（`/trade`）として動作。APIキー不要、サブスク内で完結
- 日本株10銘柄（トヨタ、ソニー、任天堂、キーエンス等）を分析
- テクニカル指標（RSI, MACD, ボリンジャーバンド, ADX, ATR）で判断
- スリッページ（0.05%）、譲渡益課税（20.315%）、損益通算を実装
- 取引結果から教訓を学習し、次回の判断に反映する
- ダークテーマのトレーディングターミナル風ダッシュボード

## セットアップ

```bash
git clone https://github.com/Moyuchiiii/claude-investment-sim.git
cd claude-investment-sim
python -m venv .venv
.venv\Scripts\activate        # Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
python scripts/setup_db.py    # DB作成 + 初期資金100万円を投入
```

## 使い方

### 売買（Claude Codeスキル）

```
/trade              # 全10銘柄を分析して売買判断
/trade 7203.T       # トヨタだけ分析
/review             # ポートフォリオの振り返り・改善提案
```

### ダッシュボード

```bash
streamlit run src/dashboard/app.py
```

または `start_terminal.bat` をダブルクリック。

### バックテスト

```bash
python scripts/backtest.py    # 全銘柄で1年分のバックテスト
```

## リセット

ポートフォリオを初期状態（100万円）に戻したい場合：

```bash
del data\sim.db               # Mac/Linux: rm data/sim.db
python scripts/setup_db.py    # 再作成
```

## 設定（config.yaml）

| 項目 | デフォルト | 説明 |
|------|-----------|------|
| `portfolio.initial_cash` | 1,000,000 | 初期資金（円） |
| `trading.max_position_pct` | 0.2 | 1銘柄への最大投資割合 |
| `trading.min_confidence` | 0.6 | 売買に必要な最低確信度 |
| `trading.stop_loss_pct` | 0.05 | 損切りライン（-5%） |
| `trading.take_profit_pct` | 0.15 | 利確ライン（+15%） |
| `trading.max_daily_trades` | 5 | 1日の最大取引回数 |
| `costs.slippage_rate` | 0.0005 | スリッページ（0.05%） |
| `costs.tax_rate` | 0.20315 | 譲渡益課税（20.315%） |
| `costs.commission_rate` | 0.0 | 売買手数料（SBI/楽天想定で0） |

## プロジェクト構成

```
claude-investment-sim/
├── config.yaml              # 設定ファイル
├── start_terminal.bat       # ダッシュボード起動用
├── data/
│   └── sim.db               # SQLiteデータベース
├── scripts/
│   ├── setup_db.py          # DB初期化
│   ├── analyze_symbol.py    # 銘柄分析（JSON出力）
│   ├── get_status.py        # ポートフォリオ状況
│   ├── execute_trade.py     # 売買実行
│   ├── record_lesson.py     # 教訓記録
│   └── backtest.py          # バックテスト
├── src/
│   ├── ai/                  # Claude連携（プロンプト構築・学習）
│   ├── data/                # 株価データ取得・テクニカル指標
│   ├── db/                  # SQLiteモデル・リポジトリ・マイグレーション
│   ├── engine/              # ポートフォリオ管理・売買実行・リスク管理
│   └── dashboard/           # Streamlitダッシュボード
├── .claude/
│   └── skills/
│       ├── trade/           # /trade スキル
│       ├── review/          # /review スキル
│       └── backtest-runner/ # バックテストスキル
└── learning/                # 学習ログ・戦略進化記録
```
