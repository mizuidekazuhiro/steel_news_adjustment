import unittest
from datetime import datetime, timezone

from src.models import NewsCandidate
from src.ranker import rank_articles


class RankerTest(unittest.TestCase):
    def test_rank_articles_orders_by_score(self) -> None:
        now = datetime.now(timezone.utc)
        a = NewsCandidate(
            title="a",
            url="https://a",
            published_at=now,
            source="s",
            query_name="q",
            region="Japan",
            category="DC Construction",
            query_priority=10,
            body_status="success",
        )
        b = NewsCandidate(
            title="b",
            url="https://b",
            published_at=now,
            source="s",
            query_name="q",
            region="Europe",
            category="Company Watch",
            query_priority=0,
            body_status="failed",
        )
        ranked = rank_articles([b, a])
        self.assertEqual(ranked[0].url, "https://a")


if __name__ == "__main__":
    unittest.main()
