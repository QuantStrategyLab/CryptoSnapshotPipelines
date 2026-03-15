from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.publish import ensure_publish_preflight
from src.release_contract import validate_release_outputs


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


class ReleaseContractValidationTests(unittest.TestCase):
    def build_outputs(
        self,
        root: Path,
        *,
        as_of_date: str = "2026-03-13",
        mode: str = "core_major",
        source_project: str = "crypto-leader-rotation",
        include_manifest: bool = False,
    ) -> None:
        output_dir = root / "data" / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        symbols = ["TRXUSDT", "ETHUSDT", "BCHUSDT", "NEARUSDT", "SOLUSDT"]
        symbol_map = {symbol: {"base_asset": symbol[:-4]} for symbol in symbols}
        version = f"{as_of_date}-{mode}"

        write_json(output_dir / "latest_universe.json", {"as_of_date": as_of_date, "symbols": symbols + ["XRPUSDT"]})
        write_json(
            output_dir / "live_pool.json",
            {
                "as_of_date": as_of_date,
                "version": version,
                "mode": mode,
                "pool_size": len(symbols),
                "symbols": symbols,
                "symbol_map": symbol_map,
                "source_project": source_project,
            },
        )
        write_json(
            output_dir / "live_pool_legacy.json",
            {
                "as_of_date": as_of_date,
                "version": version,
                "mode": mode,
                "pool_size": len(symbols),
                "symbols": symbol_map,
                "symbol_map": symbol_map,
                "source_project": source_project,
            },
        )

        pd.DataFrame(
            [
                {
                    "as_of_date": as_of_date,
                    "symbol": symbol,
                    "rule_score": 1.0 - index * 0.1,
                    "linear_score": 0.9 - index * 0.1,
                    "ml_score": 0.8 - index * 0.1,
                    "final_score": 1.0 - index * 0.1,
                    "regime": "risk_off",
                    "confidence": 0.7,
                    "selected_flag": True,
                    "current_rank": index + 1,
                }
                for index, symbol in enumerate(symbols)
            ]
        ).to_csv(output_dir / "latest_ranking.csv", index=False)

        if include_manifest:
            write_json(
                output_dir / "release_manifest.json",
                {
                    "version": version,
                    "mode": mode,
                    "dry_run": True,
                    "publish_enabled": False,
                    "as_of_date": as_of_date,
                    "release_prefix": f"crypto-leader-rotation/releases/{version}",
                    "current_prefix": "crypto-leader-rotation/current",
                    "artifacts": {},
                    "firestore": {
                        "collection": "strategy",
                        "document": "CRYPTO_LEADER_ROTATION_LIVE_POOL",
                        "payload": {
                            "as_of_date": as_of_date,
                            "version": version,
                            "mode": mode,
                            "pool_size": len(symbols),
                            "symbols": symbols,
                            "symbol_map": symbol_map,
                            "source_project": source_project,
                        },
                    },
                },
            )

    def test_validate_release_outputs_accepts_consistent_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            self.build_outputs(root, include_manifest=True)

            validation = validate_release_outputs(
                root / "data" / "output",
                expected_mode="core_major",
                expected_source_project="crypto-leader-rotation",
                expected_pool_size=5,
                reference_date="2026-03-14",
                max_age_days=45,
                require_manifest=True,
                require_freshness=True,
            )

        self.assertTrue(validation["ok"])
        self.assertEqual(validation["version"], "2026-03-13-core_major")
        self.assertEqual(validation["pool_size"], 5)
        self.assertEqual(validation["age_days"], 1)

    def test_validate_release_outputs_rejects_mismatched_manifest_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            self.build_outputs(root, include_manifest=True)
            manifest_path = root / "data" / "output" / "release_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["firestore"]["payload"]["source_project"] = "wrong-source"
            write_json(manifest_path, manifest)

            validation = validate_release_outputs(root / "data" / "output", require_manifest=True)

        self.assertFalse(validation["ok"])
        self.assertIn(
            "release_manifest.json firestore.payload source_project does not match live_pool.json",
            validation["errors"],
        )

    def test_validate_release_outputs_rejects_stale_outputs_when_required(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            self.build_outputs(root, as_of_date="2026-01-01")

            validation = validate_release_outputs(
                root / "data" / "output",
                reference_date="2026-03-15",
                max_age_days=30,
                require_freshness=True,
            )

        self.assertFalse(validation["ok"])
        self.assertTrue(any("stale" in message for message in validation["errors"]))

    def test_publish_preflight_requires_real_publish_targets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            self.build_outputs(root)

            with self.assertRaises(ValueError) as context:
                ensure_publish_preflight(
                    type(
                        "Settings",
                        (),
                        {
                            "mode": "core_major",
                            "source_project": "crypto-leader-rotation",
                            "dry_run": False,
                            "gcp_project_id": None,
                            "gcs_bucket": None,
                            "firestore_collection": "strategy",
                            "firestore_document": "CRYPTO_LEADER_ROTATION_LIVE_POOL",
                        },
                    )(),
                    root / "data" / "output",
                    expected_pool_size=5,
                    reference_date="2026-03-14",
                )

        self.assertIn("GCP_PROJECT_ID", str(context.exception))


if __name__ == "__main__":
    unittest.main()
