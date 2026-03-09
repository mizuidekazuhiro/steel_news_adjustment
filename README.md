# AI/DC鋼材モニタリング（steel_news_adjustment）README

この README は、**現在の実装コード（`src/` 配下）を読んだ事実**に基づいて、初心者向けに作り直したものです。  
「まず何を準備し、どう実行し、失敗時にどこを見るか」が分かる構成にしています。

---

## 1. このプログラムでできること

このプログラムは、以下を**1回の実行で自動処理**します。

1. Notion の「検索条件DB」から有効な検索クエリを取得
2. 各クエリで Google News RSS を検索して記事候補を収集
3. 記事URLを開いて本文を抽出（スクレイピング）
4. Notion の「結果DB」と照合してURL重複を除外
5. 記事をスコア計算して順位付けし、上位15件を選定
6. 上位15件の日本語タイトルを OpenAI API で生成
7. 上位5件のみ、要約・鋼材示唆・重要度(High/Medium/Low)を生成
8. Notion の結果DBを更新
9. HTMLメール（日次サマリ）をSMTPで送信

### 入力・出力のイメージ
- 入力
  - Notion 検索条件DBのレコード（Query, Region など）
  - 外部Web記事本文
- 出力
  - Notion 結果DBに記事データ（本文、要約、重要度など）を保存/更新
  - メール送信先（`MAIL_TO`）へサマリHTMLメール送信

---

## 2. このプログラムの全体像

実行入口は `python -m src.main` です。`run_daily_pipeline()` が全処理を順番に実行します。  
設定値は環境変数から読み込みます（`.env` も読み込み可）。

連携先は次の4つです。
- Notion API（検索条件取得、結果保存）
- Google News RSS（候補記事取得）
- OpenAI Chat Completions API（タイトル/要約生成）
- SMTPサーバー（メール送信）

---

## 3. 処理の流れ

コードの実装順に説明します。

1. ログ設定・環境変数読み込み
2. Notionクライアント、OpenAIクライアントを初期化
3. Notion検索条件DBから `Enabled = true` のクエリを取得
4. 各クエリで Google News RSS を検索（`when:1d` 付き）
5. 記事候補URLの重複を、Notion既存URL + 当日候補内重複で除外
6. 各記事をスクレイピングして本文抽出
   - 長さで `success` / `partial` / `failed` を判定
7. 記事を Notion結果DB に新規作成（本文失敗でも作成は試行）
8. ランキングスコア計算で並び替え、上位15件を選ぶ
9. 上位15件に日本語タイトル生成を実行
10. そのうち上位5件だけ要約・鋼材示唆・重要度を生成
11. Notionページを更新（Japanese Title / GPT Summary / Relevance 等）
12. 上位15件があればHTMLメールを送信

---

## 4. リポジトリ構成 / ファイル構成

```text
steel_news_adjustment/
├── src/
│   ├── main.py           # 実行入口。日次パイプライン全体
│   ├── config.py         # 環境変数の読み込み・必須チェック
│   ├── notion_client.py  # Notion API呼び出し（検索・作成・更新）
│   ├── rss_search.py     # Google News RSSから候補取得
│   ├── scraper.py        # 記事本文抽出（BeautifulSoup）
│   ├── ranker.py         # 記事スコア計算と順位付け
│   ├── summarizer.py     # OpenAI APIでタイトル/要約生成
│   ├── reporter.py       # メール件名・HTML本文生成
│   ├── mailer.py         # SMTP送信
│   ├── models.py         # データ構造（SearchQuery, NewsCandidate等）
│   └── utils.py          # ログ、リトライ、日時パース等
├── tests/
│   └── test_ranker.py    # rankerの単体テスト
├── requirements.txt
└── README.md
```

---

## 5. 事前に必要なもの

- Python 3 系（このリポジトリでは `python -m ...` 形式で実行）
- Notion アカウント
- Notion Internal Integration Token
- OpenAI API キー
- SMTP送信に使うメールアカウント情報
- インターネット接続（Notion/OpenAI/RSS/記事サイト/SMTPへ接続）

---

## 6. セットアップ手順

### 6-1. 仮想環境を作る

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 6-2. 依存ライブラリを入れる

```bash
pip install -r requirements.txt
```

### 6-3. 環境変数を設定する

このプロジェクトには `.env.example` は**現時点で存在しません**。  
そのため、`.env` を自分で作成してください。

```bash
cat > .env <<'ENV'
NOTION_TOKEN=secret_xxx
NOTION_SEARCH_QUERIES_DB_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
NOTION_NEWS_RESULTS_DB_ID=yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy
OPENAI_API_KEY=sk-xxxx
OPENAI_MODEL=gpt-4o-mini
REQUEST_TIMEOUT_SEC=20
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your_user
SMTP_PASSWORD=your_password
MAIL_FROM=sender@example.com
MAIL_TO=to1@example.com,to2@example.com
ENV
```

> 上記の値はすべてダミーです。実際の値に置き換えてください。

---

## 7. 環境変数の設定方法

`src/config.py` で読み込む値です。未設定の必須キーがあると、起動直後に `ValueError` で停止します。

| 環境変数 | 必須 | 何のために使うか | 主な利用箇所 | 未設定時 |
|---|---|---|---|---|
| `NOTION_TOKEN` | 必須 | Notion API認証 | `NotionClient` 初期化 | 起動エラー |
| `NOTION_SEARCH_QUERIES_DB_ID` | 必須 | 検索条件DBのID | クエリ取得 | 起動エラー |
| `NOTION_NEWS_RESULTS_DB_ID` | 必須 | 結果保存DBのID | 重複確認・作成・更新 | 起動エラー |
| `OPENAI_API_KEY` | 必須 | OpenAI API認証 | タイトル/要約生成 | 起動エラー |
| `OPENAI_MODEL` | 任意 | 使用モデル名 | OpenAI API呼び出し | `gpt-4o-mini` |
| `REQUEST_TIMEOUT_SEC` | 任意 | API/HTTPタイムアウト秒 | Notion/OpenAI/記事取得 | `20` |
| `SMTP_HOST` | 必須 | SMTP接続先 | メール送信 | 起動エラー |
| `SMTP_PORT` | 必須 | SMTPポート | メール送信 | 起動エラー |
| `SMTP_USER` | 必須 | SMTPログインユーザー | メール送信 | 起動エラー |
| `SMTP_PASSWORD` | 必須 | SMTPログインパスワード | メール送信 | 起動エラー |
| `MAIL_FROM` | 必須 | 送信元アドレス | メールヘッダ | 起動エラー |
| `MAIL_TO` | 必須 | 送信先（`,`区切り可） | 宛先配列化して送信 | 起動エラー |

---

## 8. Notion 側の設定方法（使っている場合）

このプログラムは Notion DB の**プロパティ名を文字列で固定参照**しています。  
そのため、以下の名前を**完全一致**で作ってください（大文字小文字・スペース含む）。

### 8-1. Search Queries DB（検索条件）

必要プロパティ:
- `Name` (title)
- `Query` (rich_text)
- `Region` (select)
- `Language` (select)
- `Priority` (number)
- `Enabled` (checkbox)
- `Category` (select)
- `Max Results` (number)

補足:
- 取得条件は `Enabled = true` の行のみ
- `Language` はコード上 `ja` 以外は `en` 扱い

### 8-2. News Results DB（結果保存）

必要プロパティ:
- `Title` (title)
- `Japanese Title` (rich_text)
- `URL` (url)
- `Published At` (date)
- `Source` (rich_text)
- `Query Name` (rich_text)
- `Region` (select)
- `Category` (select)
- `Collected At` (date)
- `Duplicate Key` (rich_text)
- `Raw Body` (rich_text)
- `Body Status` (select)
- `GPT Summary` (rich_text)
- `Steel Insight` (rich_text)
- `Relevance` (select)
- `Processing Status` (select)

推奨選択肢（コードで使われる値）:
- `Body Status`: `success`, `partial`, `failed`
- `Relevance`: `High`, `Medium`, `Low`
- `Processing Status`: `new`, `scraped`, `failed`, `title_translated`, `summarized`, `selected_for_email`

### 8-3. Notion側で忘れやすい設定

- Integration を DB に Share しないと API 403 になります。
- DB ID は URL から取得し、環境変数に設定してください。

---

## 9. 実行方法

### ローカル実行

```bash
source .venv/bin/activate
python -m src.main
```

### 定期実行するなら

このリポジトリ内にはスケジューラ実装（cron設定ファイルやGitHub Actions workflow）はありません。  
そのため、定期実行は外部で設定してください（cron / GitHub Actions / ジョブ管理基盤など）。

---

## 10. 実行結果として何が起こるか

実行後、主に次が起きます。

1. Notion結果DBに記事ページが作成される
   - 本文取得失敗でも、ページ作成は行われる設計
2. 上位15件は日本語タイトルが更新される
3. 上位5件は要約・鋼材示唆・重要度が更新される
4. `MAIL_TO` 宛てにHTMLメールが送信される

メール内容:
- 件名: `【AI/DC鋼材モニタリング】YYYY-MM-DD 日次サマリ`
- 本文: Top5（要約あり） + 6〜15位（要約なし） + 処理件数

ログ:
- 標準出力に `INFO/WARNING/ERROR` で出力
- 例外は記事単位で握りつぶさずログ出力して続行する箇所が多い

---

## 11. よくあるエラーと確認ポイント

### 1) Notion APIキー誤り / 権限不足
- 症状: 401/403
- 確認:
  - `NOTION_TOKEN` が正しいか
  - Integration が対象DBに Share されているか

### 2) Database ID の設定ミス
- 症状: クエリ取得0件、404、プロパティ取得失敗
- 確認:
  - `NOTION_SEARCH_QUERIES_DB_ID` / `NOTION_NEWS_RESULTS_DB_ID`
  - DBが本当に期待のスキーマか

### 3) OpenAI APIキー未設定/不正
- 症状: 起動時エラー or OpenAI呼び出し失敗
- 確認:
  - `OPENAI_API_KEY`
  - モデル名 (`OPENAI_MODEL`) が有効か

### 4) SMTP設定ミス
- 症状: 認証失敗、接続失敗、送信失敗
- 確認:
  - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`
  - STARTTLSに対応した設定か

### 5) RSSは取れたが本文取得に失敗
- 症状: `Body Status=failed` が増える
- 原因例:
  - 取得先サイトのブロック
  - 本文が短く、コード閾値（120文字未満）で failed 判定

### 6) Notionプロパティ名の不一致
- 症状: Notion保存/更新でエラー
- 確認:
  - README記載名とNotion実DB名が完全一致か

### 7) 環境変数未設定
- 症状: 起動直後に `Missing required environment variables` で停止
- 確認:
  - `.env` の記載漏れ

### 8) 依存ライブラリ未インストール
- 症状: `ModuleNotFoundError`
- 確認:
  - 仮想環境を有効化したか
  - `pip install -r requirements.txt` 済みか

---

## 12. このREADMEだけでは分からない点 / 要確認点

- `.env.example` はREADME旧版に記載がありましたが、現在のリポジトリには存在しません（要確認）。
- NotionのDB名称そのもの（例: "Search Queries DB"）はコード固定ではなく、**DB IDで参照**しています。名称は任意です。
- GitHub Actions の定期実行は、このリポジトリ内に workflow 定義が見当たらないため要確認です。
- Data Source ID という概念は本コードでは使っておらず、`databases/{db_id}/query` を利用しています。

---

## 13. 保守・運用するときの注意点

- Notionプロパティ名を変えると壊れます。変更時は `src/notion_client.py` を同時修正してください。
- 本文抽出は単純なCSSセレクタです。取得精度改善時は `src/scraper.py` を調整してください。
- ランキング重みは `src/ranker.py` の定数で管理されています。
- OpenAI出力はJSON前提です。パース失敗時はリトライ後に例外化されます。
- `MAIL_TO` はカンマ区切りで複数送信できます。

---

## 事実 / 前提 / 要確認 / 注意点（区別まとめ）

### 事実（コード確認済み）
- 実行入口は `src/main.py` の `run_daily_pipeline()`。
- 上位15件に日本語タイトル生成、上位5件に要約生成。
- メール送信は SMTP + STARTTLS。

### 前提（このREADMEが成り立つ条件）
- Notion/OpenAI/SMTP の認証情報が有効。
- Notion DB に必要プロパティが揃っている。

### 要確認（コードだけで断定しづらい）
- 本番運用で想定する実行頻度（1日1回以外の要件有無）。
- 送信先メールサーバーの詳細制約（IP制限・アプリパスワード要件など）。

### 注意点（ハマりやすい）
- プロパティ名の1文字違いで保存失敗。
- `.env.example` がないため手動作成が必要。
- 本文が短い記事は自動で `failed/partial` 判定になる。

---

## 初回セットアップの最短手順

1. Python仮想環境作成
2. `pip install -r requirements.txt`
3. Notionに2つのDB作成（必要プロパティを完全一致）
4. Notion Integration を2DBにShare
5. `.env` を作成して必須環境変数を設定
6. `python -m src.main` 実行
7. Notion結果DBとメール受信を確認

---

## 動作確認チェックリスト

- [ ] `python -m src.main` が起動時エラーなく走る
- [ ] Notion検索条件DBから `Enabled=true` の行を読めている
- [ ] Notion結果DBにページ作成される
- [ ] `Body Status` が `success/partial/failed` のいずれかで入る
- [ ] 上位15件に `Japanese Title` が更新される
- [ ] 上位5件に `GPT Summary` / `Steel Insight` / `Relevance` が入る
- [ ] 送信先メールに日次サマリが届く

---

## トラブル時にまず見る順番

1. 実行ログの最初（環境変数エラー）
2. Notion APIエラー（401/403/404）
3. OpenAI APIエラー
4. SMTP接続/認証エラー
5. Notionプロパティ名の一致確認
6. 記事本文取得失敗率（`Body Status`）

---

## 改修時にまず読むべきファイル

1. `src/main.py`（全体フロー）
2. `src/notion_client.py`（DBスキーマ依存箇所）
3. `src/summarizer.py`（OpenAI仕様）
4. `src/reporter.py`（メール出力）
5. `src/ranker.py`（順位ロジック）

