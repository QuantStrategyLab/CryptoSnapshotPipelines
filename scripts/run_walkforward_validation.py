#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.backtest import run_single_backtest
from src.config import load_config
from src.evaluation import evaluate_leader_selection, evaluate_live_pool_shadow, summarize_live_pool_shadow
from src.pipeline import run_research_pipeline
from src.utils import get_logger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run strict rolling walk-forward validation.")
    parser.add_argument("--config", default="config/default.yaml", help="Path to the YAML config file.")
    parser.add_argument("--universe-mode", default=None, help="Optional universe mode override, e.g. broad_liquid.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    logger = get_logger("run_walkforward_validation")

    result = run_research_pipeline(config, universe_mode=args.universe_mode)
    panel = result["panel"]
    windows = result["window_summary"].copy()

    rows = []
    for record in windows.to_dict("records"):
        test_start = pd.Timestamp(record["test_start"])
        test_end = pd.Timestamp(record["test_end"])
        date_index = panel.index.get_level_values("date")
        window_panel = panel.loc[(date_index >= test_start) & (date_index <= test_end)].copy()
        if window_panel.empty:
            continue

        leader_metrics = evaluate_leader_selection(
            window_panel,
            score_column="final_score",
            config=config,
            start_date=test_start,
            end_date=test_end,
        )
        backtest = run_single_backtest(window_panel, "final_score", config)
        row = dict(record)
        row.update(
            {
                "h30_precision": leader_metrics["30"]["Precision@N"],
                "h30_recall": leader_metrics["30"]["Recall@N"],
                "h30_capture": leader_metrics["30"]["Leader Capture Rate"],
                "h60_precision": leader_metrics["60"]["Precision@N"],
                "h60_recall": leader_metrics["60"]["Recall@N"],
                "h60_capture": leader_metrics["60"]["Leader Capture Rate"],
                "h90_precision": leader_metrics["90"]["Precision@N"],
                "h90_recall": leader_metrics["90"]["Recall@N"],
                "h90_capture": leader_metrics["90"]["Leader Capture Rate"],
                "window_cagr": backtest.metrics["CAGR"],
                "window_sharpe": backtest.metrics["Sharpe"],
                "window_max_drawdown": backtest.metrics["Max Drawdown"],
                "window_turnover": backtest.metrics["Turnover"],
            }
        )
        rows.append(row)

    validation_table = pd.DataFrame(rows)
    reports_dir = config["paths"].reports_dir
    output_path = reports_dir / "walkforward_validation_summary.csv"
    validation_table.to_csv(output_path, index=False)

    shadow_detail = evaluate_live_pool_shadow(
        panel,
        score_column="final_score",
        config=config,
        rebalance_frequency=str(config.get("release", {}).get("cadence", "monthly")),
        pool_size=int(config["export"]["live_pool_size"]),
    )
    shadow_summary = summarize_live_pool_shadow(shadow_detail)
    shadow_detail_path = reports_dir / "monthly_live_pool_shadow_detail.csv"
    shadow_summary_path = reports_dir / "monthly_live_pool_shadow_summary.csv"
    shadow_detail.to_csv(shadow_detail_path, index=False)
    shadow_summary.to_csv(shadow_summary_path, index=False)

    logger.info("Walk-forward validation saved to %s", output_path)
    logger.info("Monthly live-pool shadow validation saved to %s and %s", shadow_detail_path, shadow_summary_path)
    if not validation_table.empty:
        logger.info("Universe mode: %s", result["universe_mode"])
        logger.info("Validation head:\n%s", validation_table.head().to_string(index=False))


if __name__ == "__main__":
    main()
