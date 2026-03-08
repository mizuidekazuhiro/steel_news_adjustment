# AI/DC鋼材モニタリングシステム

## 1. このシステムで何ができるか
このシステムは、Notion で管理した検索クエリを使って Google News RSS から記事候補を収集し、本文をスクレイピングして Notion に保存、ルールベースで順位付けし、上位記事に対して OpenAI API (`gpt-4o-mini`) で日本語タイトル/要約/鋼材示唆を生成し、日次メールを配信します。

主なポイント:
- 本文は**全件** Notion に保存
- 要約は**上位5件のみ**
- 上位6〜15位は日本語タイトルのみ生成
- 重複は URL 完全一致で除外
- 本文取得失敗でも記事レコードは保存

---

## 2. 全体処理フロー
1. Search Queries DB から `Enabled=true` を取得
2. 各 Query を Google News RSS で検索
3. 候補記事を取得
4. News Results DB と URL 照合して重複除外
5. `requests + BeautifulSoup` で本文抽出
6. 本文を全件 Notion 保存
7. ルールベースで順位付け
8. 上位15件選定
9. 上位15件で日本語タイトル生成
10. 上位5件で要約・鋼材示唆・重要度生成
11. News Results DB を更新
12. 日次メール送信

---

## 3. ディレクトリ構成
```text
project/
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── notion_client.py
│   ├── rss_search.py
│   ├── scraper.py
│   ├── ranker.py
│   ├── summarizer.py
│   ├── reporter.py
│   ├── mailer.py
│   ├── models.py
│   └── utils.py
├── tests/
│   └── test_ranker.py
├── requirements.txt
├── .env.example
└── README.md
```

---

## 4. 必要な環境変数一覧
| 変数 | 必須 | 説明 |
|---|---|---|
| `NOTION_TOKEN` | 必須 | Notion Internal Integration Token |
| `NOTION_SEARCH_QUERIES_DB_ID` | 必須 | Search Queries DB ID |
| `NOTION_NEWS_RESULTS_DB_ID` | 必須 | News Results DB ID |
| `OPENAI_API_KEY` | 必須 | OpenAI APIキー |
| `OPENAI_MODEL` | 任意 | 既定値 `gpt-4o-mini` |
| `REQUEST_TIMEOUT_SEC` | 任意 | 外部APIタイムアウト秒 |
| `SMTP_HOST` | 必須 | SMTPホスト |
| `SMTP_PORT` | 必須 | SMTPポート（STARTTLS想定） |
| `SMTP_USER` | 必須 | SMTPユーザー |
| `SMTP_PASSWORD` | 必須 | SMTPパスワード |
| `MAIL_FROM` | 必須 | 送信元メール |
| `MAIL_TO` | 必須 | 送信先（カンマ区切り可） |

---

## 5. Notion側で必要なDB構成
2つのDBを作成してください。

1. **Search Queries DB**（検索条件管理）
2. **News Results DB**（収集・解析結果）

必ずプロパティ名を完全一致で作成してください（半角スペース含む）。

---

## 6. Search Queries DB の作り方
### 必須プロパティ
- `Name` : title
- `Query` : rich_text
- `Region` : select
- `Language` : select
- `Priority` : number
- `Enabled` : checkbox
- `Category` : select
- `Max Results` : number

### `Region` の select 値
- Japan
- India
- ASEAN
- Korea
- Taiwan
- China
- Middle East
- Australia
- US
- Europe
- Global

### `Language` の select 値
- ja
- en

### `Category` の select 値
- AI Investment
- DC Construction
- Power
- Cooling
- Steel
- Company Watch

---

## 7. News Results DB の作り方
### 必須プロパティ
- `Title` : title
- `Japanese Title` : rich_text
- `URL` : url
- `Published At` : date
- `Source` : rich_text
- `Query Name` : rich_text
- `Region` : select
- `Category` : select
- `Collected At` : date
- `Duplicate Key` : rich_text
- `Raw Body` : rich_text
- `Body Status` : select
- `GPT Summary` : rich_text
- `Steel Insight` : rich_text
- `Relevance` : select
- `Processing Status` : select

### `Body Status` の select 値
- success
- partial
- failed

### `Relevance` の select 値
- High
- Medium
- Low

### `Processing Status` の select 値
- new
- scraped
- selected_for_email
- title_translated
- summarized
- failed

---

## 8. .env の設定方法
1. `.env.example` を `.env` にコピー
2. Notion/OpenAI/SMTPの実値を入力
3. `OPENAI_MODEL` は `gpt-4o-mini` のまま推奨

```bash
cp .env.example .env
```

---

## 9. セットアップ手順
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# .env を編集
```

---

## 10. ローカル実行方法
```bash
python -m src.main
```

---

## 11. 日次実行の想定方法
スケジューラ実装は含みません。以下を外部で設定してください。
- cron
- GitHub Actions scheduled workflow
- Cloud Scheduler + job runner

例（cron）:
```cron
0 7 * * * cd /path/to/project && /path/to/.venv/bin/python -m src.main >> monitor.log 2>&1
```

---

## 12. メール送信設定
- SMTP は STARTTLS を想定
- 件名: `【AI/DC鋼材モニタリング】YYYY-MM-DD 日次サマリ`
- 最大15件掲載
- リンクテキストは必ず `Japanese Title`

---

## 13. OpenAI APIの使用箇所
本実装は OpenAI HTTP API を `requests` で直接呼び出します。

- モデル: `gpt-4o-mini`
- 上位15件: 日本語タイトル生成
- 上位5件: 日本語タイトル + 要約 + 鋼材示唆 + 重要度
- 出力形式: JSON強制 (`response_format: json_object`)
- JSONパース失敗時: 最小限リトライ

---

## 14. ランキングロジックの説明
スコア合計方式（高い順）:
1. 地域優先度
2. カテゴリ優先度
3. Search Query の `Priority`
4. 本文取得ステータス（success > partial > failed）
5. 公開日時の新しさ（24時間以内を加点）

カテゴリ優先:
1. DC Construction
2. Power
3. Steel
4. AI Investment
5. Cooling
6. Company Watch

---

## 15. エラー時の見方
- ログは標準出力に `INFO/WARNING/ERROR` で出力
- APIタイムアウト・HTTP異常・JSON異常時は例外ログ
- 1件失敗しても全体停止しにくいよう、記事単位で継続処理

---

## 16. よくある失敗
1. **Notionのプロパティ名不一致**
   - 完全一致必須。特に `Max Results`, `Duplicate Key`, `Processing Status`。
2. **Notion Integration 未共有**
   - DBに Integration を Share していないと 403。
3. **OpenAIキー不備**
   - `OPENAI_API_KEY` 未設定/失効。
4. **SMTP認証エラー**
   - アプリパスワード未設定、ポート不一致。
5. **スクレイピング失敗**
   - サイト側ブロックや本文不足で `failed/partial`。
   - この場合でも記事はNotionに保存され、要約はスキップされます。

---

## 17. 今後の拡張候補
- URL正規化強化（追跡パラメータ除去）
- Notion URL重複チェックのバッチ最適化
- メール本文テンプレートの多言語化
- 送信先の部門別配信
- 重要度判定の説明文追加

---

## まず何を作れば動くか（最短順）
1. Notion Integration 作成 + Token取得
2. Search Queries DB を作る（プロパティ完全一致）
3. News Results DB を作る（プロパティ完全一致）
4. 各DBへ Integration を Share
5. `.env` を埋める
6. `python -m src.main` を実行
7. Notion登録結果とメール受信を確認

