from __future__ import annotations

import unittest
from unittest.mock import patch

import pandas as pd

from src.export import build_live_pool_payload
from src.ranking import build_final_scores, latest_ranking_snapshot


class RankingTieBreakTests(unittest.TestCase):
    def test_tie_break_prefers_confidence_then_liquidity_then_symbol(self) -> None:
        as_of_date = pd.Timestamp("2026-04-01")
        index = pd.MultiIndex.from_tuples(
            [
                (as_of_date, "AAAUSDT"),
                (as_of_date, "BBBUSDT"),
                (as_of_date, "CCCUSDT"),
            ],
            names=["date", "symbol"],
        )
        panel = pd.DataFrame(
            {
                "in_universe": [True, True, True],
                "rule_score": [1.0, 0.5, 0.5],
                "linear_score_raw": [0.0, 0.5, 0.5],
                "ml_score_raw": [0.5, 0.5, 0.5],
                "regime": ["risk_off", "risk_off", "risk_off"],
                "liquidity_stability": [0.70, 0.90, 0.80],
                "avg_quote_vol_180": [20_000_000.0, 30_000_000.0, 30_000_000.0],
            },
            index=index,
        )
        config = {
            "ensemble": {"default_weights": {"rule_score": 1.0, "linear_score": 1.0, "ml_score": 1.0}},
            "regime_weights": {},
            "ranking": {"selected_pool_size": 2},
        }

        with patch("src.ranking.normalize_component_by_date", side_effect=lambda frame, column, mask: frame[column]):
            scored = build_final_scores(panel, config)

        snapshot = latest_ranking_snapshot(scored, as_of_date)
        self.assertEqual(snapshot.index.tolist(), ["BBBUSDT", "CCCUSDT", "AAAUSDT"])
        self.assertEqual(snapshot["current_rank"].tolist(), [1.0, 2.0, 3.0])
        self.assertEqual(snapshot.loc[snapshot["selected_flag"]].index.tolist(), ["BBBUSDT", "CCCUSDT"])

    def test_live_pool_payload_uses_same_deterministic_tie_break(self) -> None:
        as_of_date = pd.Timestamp("2026-04-01")
        ranking_snapshot = pd.DataFrame(
            {
                "final_score": [0.5, 0.5, 0.5],
                "confidence": [0.6, 0.6, 0.6],
                "liquidity_stability": [0.80, 0.80, 0.80],
                "avg_quote_vol_180": [15_000_000.0, 25_000_000.0, 25_000_000.0],
            },
            index=pd.Index(["CCCUSDT", "BBBUSDT", "AAAUSDT"], name="symbol"),
        )
        metadata = pd.DataFrame(
            {
                "symbol": ["AAAUSDT", "BBBUSDT", "CCCUSDT"],
                "base_asset": ["AAA", "BBB", "CCC"],
            }
        )

        payload, _ = build_live_pool_payload(
            ranking_snapshot=ranking_snapshot,
            metadata=metadata,
            as_of_date=as_of_date,
            pool_size=2,
            mode="core_major",
        )

        self.assertEqual(payload["symbols"], ["AAAUSDT", "BBBUSDT"])


if __name__ == "__main__":
    unittest.main()
