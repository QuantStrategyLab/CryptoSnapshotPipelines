from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .regime import get_regime_weights
from .utils import normalize_component_by_date


def sort_ranking_snapshot(snapshot: pd.DataFrame) -> pd.DataFrame:
    """Apply a deterministic ranking order with explicit tie-breaks."""
    ordered = snapshot.copy()
    added_columns: list[str] = []
    for column in ("confidence", "liquidity_stability", "avg_quote_vol_180"):
        if column not in ordered.columns:
            ordered[column] = np.nan
            added_columns.append(column)

    ordered["_sort_symbol"] = pd.Index(ordered.index).astype(str).str.upper()
    ordered = ordered.sort_values(
        ["final_score", "confidence", "liquidity_stability", "avg_quote_vol_180", "_sort_symbol"],
        ascending=[False, False, False, False, True],
        na_position="last",
        kind="mergesort",
    )
    return ordered.drop(columns=["_sort_symbol", *added_columns], errors="ignore")


def merge_predictions(panel: pd.DataFrame, predictions: pd.DataFrame) -> pd.DataFrame:
    """Attach model prediction columns to the main panel."""
    if predictions.empty:
        panel["linear_score_raw"] = np.nan
        panel["ml_score_raw"] = np.nan
        panel["prediction_window_count"] = 0
        return panel
    return panel.join(predictions, how="left")


def build_final_scores(panel: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Normalize score components, apply regime weights, and flag selected names."""
    panel = panel.copy()
    universe_mask = panel["in_universe"] & panel["rule_score"].notna()

    panel["rule_score"] = normalize_component_by_date(panel, "rule_score", universe_mask)
    if "linear_score_raw" in panel.columns:
        panel["linear_score"] = normalize_component_by_date(panel, "linear_score_raw", universe_mask)
    else:
        panel["linear_score"] = np.nan
    if "ml_score_raw" in panel.columns:
        panel["ml_score"] = normalize_component_by_date(panel, "ml_score_raw", universe_mask)
    else:
        panel["ml_score"] = np.nan

    default_weights = config["ensemble"]["default_weights"]
    component_names = ["rule_score", "linear_score", "ml_score"]
    for component in component_names:
        panel[f"{component}_weight"] = float(default_weights.get(component, 0.0))

    for regime_name in panel["regime"].dropna().unique():
        regime_weights = get_regime_weights(regime_name, config)
        regime_mask = panel["regime"].eq(regime_name)
        for component in component_names:
            panel.loc[regime_mask, f"{component}_weight"] = float(regime_weights.get(component, 0.0))

    weighted_sum = pd.Series(0.0, index=panel.index)
    effective_weight = pd.Series(0.0, index=panel.index)
    for component in component_names:
        component_weight = panel[f"{component}_weight"]
        component_value = panel[component]
        valid = component_value.notna()
        weighted_sum = weighted_sum.add(component_value.fillna(0.0) * component_weight, fill_value=0.0)
        effective_weight = effective_weight.add(component_weight.where(valid, 0.0), fill_value=0.0)

    panel["final_score"] = weighted_sum / effective_weight.replace(0.0, np.nan)

    component_frame = panel[component_names]
    agreement = 1.0 - component_frame.std(axis=1, skipna=True).fillna(0.5).clip(0.0, 0.5) * 2.0
    edge = (panel["final_score"] - 0.5).abs() * 2.0
    panel["confidence"] = (0.6 * agreement + 0.4 * edge).clip(0.0, 1.0)
    panel["selected_flag"] = False
    panel["current_rank"] = np.nan

    pool_size = int(config["ranking"]["selected_pool_size"])
    for date, group in panel.groupby(level="date"):
        eligible = group.loc[group["in_universe"] & group["final_score"].notna()].copy()
        if eligible.empty:
            continue
        ordered = sort_ranking_snapshot(eligible)
        panel.loc[ordered.index, "current_rank"] = np.arange(1, len(ordered) + 1, dtype=float)
        selected = ordered.head(pool_size)
        panel.loc[selected.index, "selected_flag"] = True

    if "prediction_window_count" in panel.columns:
        oos_mask = panel["prediction_window_count"].fillna(0).astype(float) > 0
        panel.loc[~oos_mask, "final_score"] = np.nan
        panel.loc[~oos_mask, "confidence"] = np.nan
        panel.loc[~oos_mask, "current_rank"] = np.nan
        panel.loc[~oos_mask, "selected_flag"] = False

    return panel


def latest_ranking_snapshot(panel: pd.DataFrame, as_of_date: pd.Timestamp | str) -> pd.DataFrame:
    """Return one date slice sorted by the current final score."""
    snapshot = panel.xs(pd.Timestamp(as_of_date), level="date").copy()
    if "final_score" in snapshot.columns:
        snapshot = sort_ranking_snapshot(snapshot)
    return snapshot
