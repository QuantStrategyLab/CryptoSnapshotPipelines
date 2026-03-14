#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import load_config
from src.pipeline import run_research_pipeline
from src.shadow import build_shadow_release_history, summarize_shadow_release_history
from src.utils import ensure_directory, get_logger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build additive dual-track shadow candidate releases for the baseline reference and challenger_topk_60."
    )
    parser.add_argument("--config", default="config/default.yaml", help="Path to the YAML config file.")
    parser.add_argument("--universe-mode", default=None, help="Optional research universe mode override.")
    parser.add_argument(
        "--root-subdir",
        default=None,
        help="Optional override for the shadow candidate output root under data/output/.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logger = get_logger("build_shadow_candidate_tracks")
    base_config = load_config(args.config)
    shadow_cfg = base_config.get("shadow_replay", {})
    candidate_cfg = base_config.get("shadow_candidates", {})

    root_subdir = args.root_subdir or str(candidate_cfg.get("root_dir", "data/output/shadow_candidate_tracks"))
    if root_subdir.startswith("data/output/"):
        output_root = ensure_directory(base_config["paths"].output_dir / root_subdir.replace("data/output/", "", 1))
    else:
        output_root = ensure_directory(base_config["paths"].project_root / root_subdir)

    include_selection_meta = bool(candidate_cfg.get("include_selection_meta", shadow_cfg.get("include_selection_meta", True)))
    selection_meta_fields = (
        list(shadow_cfg.get("selection_meta_fields", []))
        if include_selection_meta
        else None
    )

    track_rows = []
    for track in candidate_cfg.get("tracks", []):
        target_mode = str(track["target_mode"])
        profile_name = str(track["profile_name"])
        track_id = str(track["track_id"])
        source_track = str(track["source_track"])
        candidate_status = str(track["candidate_status"])

        logger.info("Building shadow track %s (%s)", track_id, target_mode)
        config = load_config(args.config, overrides={"labels": {"target_mode": target_mode}})
        result = run_research_pipeline(config, universe_mode=args.universe_mode)
        track_dir = ensure_directory(output_root / track_id)
        index_table = build_shadow_release_history(
            panel=result["panel"],
            metadata=result["metadata"],
            config=config,
            output_dir=track_dir,
            cadence=str(shadow_cfg.get("cadence", "monthly")),
            activation_lag_days=int(shadow_cfg.get("activation_lag_days", 1)),
            selection_meta_fields=selection_meta_fields,
            profile_name=profile_name,
            source_track=source_track,
            candidate_status=candidate_status,
        )
        summary = summarize_shadow_release_history(index_table).iloc[0].to_dict()
        track_rows.append(
            {
                "track_id": track_id,
                "profile_name": profile_name,
                "target_mode": target_mode,
                "source_track": source_track,
                "candidate_status": candidate_status,
                "release_count": int(summary.get("release_count", 0)),
                "first_as_of_date": summary.get("first_as_of_date", ""),
                "last_as_of_date": summary.get("last_as_of_date", ""),
                "release_index_path": str((track_dir / "release_index.csv").relative_to(base_config["paths"].project_root)),
            }
        )

    summary_table = pd.DataFrame(track_rows)
    summary_path = output_root / "track_summary.csv"
    summary_table.to_csv(summary_path, index=False)
    logger.info("Shadow candidate track summary saved to %s", summary_path)
    if not summary_table.empty:
        logger.info("Track summary:\n%s", summary_table.to_string(index=False))


if __name__ == "__main__":
    main()
