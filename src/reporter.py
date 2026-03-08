from __future__ import annotations

from datetime import date
from html import escape

from src.models import NewsCandidate, RunStats


def build_daily_subject(today: date) -> str:
    return f"【AI/DC鋼材モニタリング】{today.isoformat()} 日次サマリ"


def build_daily_html(top15: list[NewsCandidate], stats: RunStats) -> str:
    top5 = top15[:5]
    other = top15[5:15]
    insight_lines = [f"<li>{escape(x.steel_insight or '不明')}</li>" for x in top5]
    return f"""
<html><body style='font-family: Arial, sans-serif; line-height: 1.6;'>
<h2>1. 本日の総括</h2>
<p>AI成長に伴うデータセンター向け鋼材供給機会を監視し、重要ニュースを抽出しました。</p>
<h2>2. 重要記事 Top 5（要約あり）</h2>
{''.join(_render_top_item(i, n) for i, n in enumerate(top5, start=1))}
<h2>3. その他注目記事 6〜15位（要約なし）</h2>
{''.join(_render_other_item(i, n) for i, n in enumerate(other, start=6))}
<h2>4. 鋼材示唆まとめ</h2><ul>{''.join(insight_lines)}</ul>
<h2>5. 処理件数サマリ</h2>
<ul>
<li>取得クエリ数: {stats.fetched_queries}</li>
<li>RSS候補件数: {stats.rss_candidates}</li>
<li>重複除外: {stats.duplicates_skipped}</li>
<li>本文保存件数: {stats.saved_raw}</li>
<li>本文success/partial/failed: {stats.scraped_success}/{stats.scraped_partial}/{stats.scraped_failed}</li>
<li>メール候補(Top15): {stats.selected_top15}</li>
<li>要約対象(Top5): {stats.summarized_top5}</li>
</ul>
</body></html>
""".strip()


def _render_top_item(rank: int, item: NewsCandidate) -> str:
    title = escape(item.japanese_title or "不明")
    return (
        f"<div><h3>{rank}. <a href='{escape(item.url)}'>{title}</a></h3>"
        f"<p>公開日: {escape(item.published_at.isoformat() if item.published_at else '不明')} / "
        f"ソース: {escape(item.source or '不明')} / 地域: {escape(item.region)} / "
        f"カテゴリ: {escape(item.category)} / 重要度: {escape(item.relevance)}</p>"
        f"<p>要約: {escape(item.summary or '不明')}</p>"
        f"<p>鋼材示唆: {escape(item.steel_insight or '不明')}</p></div>"
    )


def _render_other_item(rank: int, item: NewsCandidate) -> str:
    title = escape(item.japanese_title or "不明")
    return (
        f"<div><p>{rank}. <a href='{escape(item.url)}'>{title}</a>"
        f" / 公開日: {escape(item.published_at.isoformat() if item.published_at else '不明')}"
        f" / ソース: {escape(item.source or '不明')} / 地域: {escape(item.region)}"
        f" / カテゴリ: {escape(item.category)} / 重要度: {escape(item.relevance)}</p></div>"
    )
