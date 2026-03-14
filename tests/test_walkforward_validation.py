from __future__ import annotations

import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from src.backtest import (
    aggregate_walkforward_predictions,
    build_walkforward_windows,
    run_walkforward_scoring,
)
from src.evaluation import evaluate_live_pool_shadow, summarize_live_pool_shadow
from src.models import ModelPredictionResult


class WalkforwardValidationTests(unittest.TestCase):
    def test_build_walkforward_windows_defaults_purge_to_max_label_horizon(self) -> None:
        dates = list(pd.date_range("2024-01-01", periods=8, freq="D"))
        config = {
            "walkforward": {
                "train_window_days": 4,
                "test_window_days": 2,
                "step_days": 2,
                "purge_days": None,
            },
            "labels": {"horizons": [1, 2]},
        }

        windows = build_walkforward_windows(dates, config)

        self.assertEqual(windows[0]["purge_days"], 2)
        self.assertEqual(windows[0]["train_end"], pd.Timestamp("2024-01-04"))
        self.assertEqual(windows[0]["effective_train_end"], pd.Timestamp("2024-01-02"))

    def test_run_walkforward_scoring_uses_effective_train_end(self) -> None:
        dates = pd.date_range("2024-01-01", periods=8, freq="D")
        symbols = ["AAA", "BBB"]
        index = pd.MultiIndex.from_product([dates, symbols], names=["date", "symbol"])
        panel = pd.DataFrame(index=index)
        panel["in_universe"] = True
        panel["blended_target"] = 1.0
        panel["feature_a"] = 1.0

        config = {
            "walkforward": {
                "train_window_days": 4,
                "test_window_days": 2,
                "step_days": 2,
                "purge_days": 1,
                "prediction_aggregation": "mean",
            },
            "labels": {"horizons": [1, 2]},
            "model": {"min_train_rows": 1},
        }

        captured_train_max_dates: list[pd.Timestamp] = []

        def fake_fit_predict_models(
            train_df: pd.DataFrame,
            score_df: pd.DataFrame,
            feature_columns: list[str],
            config: dict[str, object],
        ) -> ModelPredictionResult:
            captured_train_max_dates.append(train_df.index.get_level_values("date").max())
            predictions = pd.DataFrame(index=score_df.index)
            predictions["linear_score_raw"] = np.arange(len(score_df), dtype=float)
            predictions["ml_score_raw"] = np.arange(len(score_df), dtype=float)
            return ModelPredictionResult(
                predictions=predictions,
                linear_backend="fake_linear",
                ml_backend="fake_ml",
                train_rows=len(train_df),
                test_rows=len(score_df),
            )

        with patch("src.backtest.fit_predict_models", fake_fit_predict_models):
            scored, window_summary = run_walkforward_scoring(panel, ["feature_a"], config)

        self.assertEqual(captured_train_max_dates[0], pd.Timestamp("2024-01-03"))
        self.assertEqual(int(window_summary.iloc[0]["train_rows_pre_purge"]), 8)
        self.assertEqual(int(window_summary.iloc[0]["purged_train_rows"]), 2)
        self.assertEqual(int(scored["prediction_window_count"].max()), 1)

    def test_aggregate_walkforward_predictions_supports_latest_mode(self) -> None:
        index = pd.MultiIndex.from_tuples(
            [
                (pd.Timestamp("2024-02-01"), "AAA"),
                (pd.Timestamp("2024-02-01"), "AAA"),
                (pd.Timestamp("2024-02-01"), "BBB"),
            ],
            names=["date", "symbol"],
        )
        prediction_frame = pd.DataFrame(
            {
                "linear_score_raw": [1.0, 3.0, 2.0],
                "ml_score_raw": [5.0, 7.0, 4.0],
                "window_id": [0, 1, 1],
            },
            index=index,
        )

        mean_aggregated = aggregate_walkforward_predictions(prediction_frame, aggregation_mode="mean")
        latest_aggregated = aggregate_walkforward_predictions(prediction_frame, aggregation_mode="latest")

        mean_row = mean_aggregated.loc[(pd.Timestamp("2024-02-01"), "AAA")]
        latest_row = latest_aggregated.loc[(pd.Timestamp("2024-02-01"), "AAA")]

        self.assertEqual(mean_row["linear_score_raw"], 2.0)
        self.assertEqual(mean_row["prediction_window_count"], 2)
        self.assertEqual(latest_row["linear_score_raw"], 3.0)
        self.assertEqual(latest_row["prediction_window_count"], 2)
        self.assertEqual(latest_row["prediction_source_window_id"], 1)

    def test_evaluate_live_pool_shadow_and_summary(self) -> None:
        dates = [pd.Timestamp("2024-01-31"), pd.Timestamp("2024-02-29")]
        symbols = ["AAA", "BBB", "CCC"]
        index = pd.MultiIndex.from_product([dates, symbols], names=["date", "symbol"])
        panel = pd.DataFrame(index=index)
        panel["in_universe"] = True
        panel["final_score"] = [
            0.9, 0.8, 0.1,
            0.2, 0.95, 0.85,
        ]
        panel["future_return_30"] = [
            0.4, 0.2, 0.1,
            0.0, 0.1, 0.5,
        ]

        config = {
            "export": {"live_pool_size": 2},
            "labels": {"horizons": [30], "future_top_k": 1},
        }

        shadow = evaluate_live_pool_shadow(
            panel,
            score_column="final_score",
            config=config,
            rebalance_frequency="monthly",
            pool_size=2,
        )
        summary = summarize_live_pool_shadow(shadow)

        self.assertEqual(len(shadow), 2)
        self.assertEqual(shadow.iloc[0]["pool_symbols"], "AAA,BBB")
        self.assertEqual(shadow.iloc[1]["pool_symbols"], "BBB,CCC")
        self.assertEqual(shadow.iloc[1]["pool_churn"], 0.5)
        self.assertEqual(shadow.iloc[0]["h30_precision"], 0.5)
        self.assertEqual(shadow.iloc[1]["h30_leader_capture"], 1.0)
        self.assertEqual(int(summary.iloc[0]["evaluation_dates"]), 2)
        self.assertEqual(summary.iloc[0]["pool_churn"], 0.5)
        self.assertEqual(summary.iloc[0]["h30_precision"], 0.5)


if __name__ == "__main__":
    unittest.main()
