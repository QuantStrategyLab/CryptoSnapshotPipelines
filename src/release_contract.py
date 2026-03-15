from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .utils import read_json


REQUIRED_OUTPUT_FILES = (
    "latest_universe.json",
    "latest_ranking.csv",
    "live_pool.json",
    "live_pool_legacy.json",
)
REQUIRED_MANIFEST_FILE = "release_manifest.json"
REQUIRED_RANKING_COLUMNS = (
    "as_of_date",
    "symbol",
    "rule_score",
    "linear_score",
    "ml_score",
    "final_score",
    "regime",
    "confidence",
    "selected_flag",
    "current_rank",
)
REQUIRED_LIVE_POOL_FIELDS = (
    "as_of_date",
    "version",
    "mode",
    "pool_size",
    "symbols",
    "symbol_map",
    "source_project",
)


def build_release_version(as_of_date: str, mode: str) -> str:
    return f"{as_of_date}-{mode}"


def _parse_as_of_date(value: Any) -> tuple[str, pd.Timestamp | None]:
    if not isinstance(value, str) or not value.strip():
        return "", None
    try:
        parsed = pd.Timestamp(value[:10]).normalize()
    except Exception:
        return str(value).strip(), None
    return parsed.strftime("%Y-%m-%d"), parsed


def _append_missing_fields(payload: dict[str, Any], required_fields: tuple[str, ...], errors: list[str], label: str) -> None:
    for field in required_fields:
        if field not in payload:
            errors.append(f"{label} missing field: {field}")


def _validate_symbol(symbol: Any, field_label: str, errors: list[str]) -> str:
    if not isinstance(symbol, str) or not symbol.strip():
        errors.append(f"{field_label} contains an empty symbol")
        return ""
    normalized = symbol.strip().upper()
    if not normalized.endswith("USDT"):
        errors.append(f"{field_label} contains non-USDT symbol: {normalized}")
        return ""
    return normalized


def _normalize_symbol_list(symbols: Any, field_label: str, errors: list[str]) -> list[str]:
    if not isinstance(symbols, list) or not symbols:
        errors.append(f"{field_label} must be a non-empty list")
        return []

    normalized: list[str] = []
    seen: set[str] = set()
    for raw_symbol in symbols:
        symbol = _validate_symbol(raw_symbol, field_label, errors)
        if not symbol:
            continue
        if symbol in seen:
            errors.append(f"{field_label} contains duplicate symbol: {symbol}")
            continue
        normalized.append(symbol)
        seen.add(symbol)
    return normalized


def _normalize_symbol_map(symbol_map: Any, field_label: str, errors: list[str]) -> dict[str, dict[str, str]]:
    if not isinstance(symbol_map, dict) or not symbol_map:
        errors.append(f"{field_label} must be a non-empty mapping")
        return {}

    normalized: dict[str, dict[str, str]] = {}
    for raw_symbol, raw_meta in symbol_map.items():
        symbol = _validate_symbol(raw_symbol, field_label, errors)
        if not symbol:
            continue
        if not isinstance(raw_meta, dict):
            errors.append(f"{field_label}[{symbol}] must be an object")
            continue
        base_asset = str(raw_meta.get("base_asset", "")).strip().upper()
        if not base_asset:
            errors.append(f"{field_label}[{symbol}] missing base_asset")
            continue
        normalized[symbol] = {"base_asset": base_asset}
    return normalized


def _normalize_pool_size(value: Any, field_label: str, errors: list[str]) -> int | None:
    try:
        parsed = int(value)
    except Exception:
        errors.append(f"{field_label} must be an integer")
        return None
    if parsed <= 0:
        errors.append(f"{field_label} must be positive")
        return None
    return parsed


def _normalize_source_project(value: Any, field_label: str, errors: list[str]) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        errors.append(f"{field_label} must be a non-empty string")
    return normalized


def _coerce_selected_flag(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    return (
        series.fillna(False)
        .astype(str)
        .str.strip()
        .str.lower()
        .isin({"1", "true", "yes", "y", "on"})
    )


def validate_release_outputs(
    output_dir: Path | str,
    *,
    expected_mode: str | None = None,
    expected_source_project: str | None = None,
    expected_pool_size: int | None = None,
    reference_date: Any = None,
    max_age_days: int | None = None,
    require_manifest: bool = False,
    require_freshness: bool = False,
) -> dict[str, Any]:
    output_path = Path(output_dir)
    errors: list[str] = []
    warnings: list[str] = []
    loaded_files: dict[str, Any] = {}

    for filename in REQUIRED_OUTPUT_FILES:
        path = output_path / filename
        if not path.exists():
            errors.append(f"missing required output: {path}")
            continue
        loaded_files[filename] = path

    manifest_path = output_path / REQUIRED_MANIFEST_FILE
    manifest_present = manifest_path.exists()
    if require_manifest and not manifest_present:
        errors.append(f"missing required output: {manifest_path}")
    elif manifest_present:
        loaded_files[REQUIRED_MANIFEST_FILE] = manifest_path

    if errors:
        return {
            "ok": False,
            "errors": errors,
            "warnings": warnings,
            "output_dir": str(output_path),
            "manifest_present": manifest_present,
        }

    latest_universe = read_json(loaded_files["latest_universe.json"], default={}) or {}
    live_pool = read_json(loaded_files["live_pool.json"], default={}) or {}
    live_pool_legacy = read_json(loaded_files["live_pool_legacy.json"], default={}) or {}
    manifest = read_json(manifest_path, default={}) or {}

    ranking_path = loaded_files["latest_ranking.csv"]
    try:
        latest_ranking = pd.read_csv(ranking_path)
    except Exception as exc:
        errors.append(f"failed to read latest_ranking.csv: {exc}")
        latest_ranking = pd.DataFrame()

    if not isinstance(latest_universe, dict):
        errors.append("latest_universe.json must contain an object")
        latest_universe = {}
    if not isinstance(live_pool, dict):
        errors.append("live_pool.json must contain an object")
        live_pool = {}
    if not isinstance(live_pool_legacy, dict):
        errors.append("live_pool_legacy.json must contain an object")
        live_pool_legacy = {}
    if manifest_present and not isinstance(manifest, dict):
        errors.append("release_manifest.json must contain an object")
        manifest = {}

    _append_missing_fields(live_pool, REQUIRED_LIVE_POOL_FIELDS, errors, "live_pool.json")
    _append_missing_fields(live_pool_legacy, REQUIRED_LIVE_POOL_FIELDS, errors, "live_pool_legacy.json")

    universe_symbols = _normalize_symbol_list(
        latest_universe.get("symbols"),
        "latest_universe.json symbols",
        errors,
    )
    live_pool_symbols = _normalize_symbol_list(live_pool.get("symbols"), "live_pool.json symbols", errors)
    live_pool_symbol_map = _normalize_symbol_map(
        live_pool.get("symbol_map"),
        "live_pool.json symbol_map",
        errors,
    )
    legacy_symbols = _normalize_symbol_map(
        live_pool_legacy.get("symbols"),
        "live_pool_legacy.json symbols",
        errors,
    )
    legacy_symbol_map = _normalize_symbol_map(
        live_pool_legacy.get("symbol_map"),
        "live_pool_legacy.json symbol_map",
        errors,
    )

    live_pool_size = _normalize_pool_size(live_pool.get("pool_size"), "live_pool.json pool_size", errors)
    legacy_pool_size = _normalize_pool_size(
        live_pool_legacy.get("pool_size"),
        "live_pool_legacy.json pool_size",
        errors,
    )
    live_pool_mode = str(live_pool.get("mode", "")).strip()
    legacy_mode = str(live_pool_legacy.get("mode", "")).strip()
    if not live_pool_mode:
        errors.append("live_pool.json mode must be a non-empty string")
    if not legacy_mode:
        errors.append("live_pool_legacy.json mode must be a non-empty string")

    live_pool_source_project = _normalize_source_project(
        live_pool.get("source_project"),
        "live_pool.json source_project",
        errors,
    )
    legacy_source_project = _normalize_source_project(
        live_pool_legacy.get("source_project"),
        "live_pool_legacy.json source_project",
        errors,
    )

    universe_as_of_date, universe_as_of_ts = _parse_as_of_date(latest_universe.get("as_of_date"))
    live_pool_as_of_date, live_pool_as_of_ts = _parse_as_of_date(live_pool.get("as_of_date"))
    legacy_as_of_date, legacy_as_of_ts = _parse_as_of_date(live_pool_legacy.get("as_of_date"))
    if universe_as_of_ts is None:
        errors.append("latest_universe.json as_of_date is missing or invalid")
    if live_pool_as_of_ts is None:
        errors.append("live_pool.json as_of_date is missing or invalid")
    if legacy_as_of_ts is None:
        errors.append("live_pool_legacy.json as_of_date is missing or invalid")

    live_pool_version = str(live_pool.get("version", "")).strip()
    legacy_version = str(live_pool_legacy.get("version", "")).strip()
    if not live_pool_version:
        errors.append("live_pool.json version must be a non-empty string")
    if not legacy_version:
        errors.append("live_pool_legacy.json version must be a non-empty string")

    if live_pool_symbols and live_pool_symbol_map and set(live_pool_symbols) != set(live_pool_symbol_map):
        errors.append("live_pool.json symbols and symbol_map keys do not match")
    if legacy_symbols and legacy_symbol_map and legacy_symbols != legacy_symbol_map:
        errors.append("live_pool_legacy.json symbols and symbol_map must be identical mappings")
    if live_pool_symbols and legacy_symbols and set(live_pool_symbols) != set(legacy_symbols):
        errors.append("live_pool.json symbols do not match live_pool_legacy.json symbols")
    if live_pool_size is not None and live_pool_symbols and live_pool_size != len(live_pool_symbols):
        errors.append(
            f"live_pool.json pool_size mismatch: declared {live_pool_size} vs parsed {len(live_pool_symbols)}"
        )
    if legacy_pool_size is not None and legacy_symbols and legacy_pool_size != len(legacy_symbols):
        errors.append(
            f"live_pool_legacy.json pool_size mismatch: declared {legacy_pool_size} vs parsed {len(legacy_symbols)}"
        )
    if universe_symbols and live_pool_symbols and not set(live_pool_symbols).issubset(set(universe_symbols)):
        errors.append("live_pool.json symbols must be a subset of latest_universe.json symbols")

    if live_pool_as_of_date and live_pool_mode:
        expected_version = build_release_version(live_pool_as_of_date, live_pool_mode)
        if live_pool_version and live_pool_version != expected_version:
            errors.append(f"live_pool.json version mismatch: expected {expected_version} got {live_pool_version}")
    if legacy_as_of_date and legacy_mode:
        expected_legacy_version = build_release_version(legacy_as_of_date, legacy_mode)
        if legacy_version and legacy_version != expected_legacy_version:
            errors.append(
                f"live_pool_legacy.json version mismatch: expected {expected_legacy_version} got {legacy_version}"
            )

    as_of_values = {value for value in (universe_as_of_date, live_pool_as_of_date, legacy_as_of_date) if value}
    if not latest_ranking.empty and "as_of_date" in latest_ranking.columns:
        as_of_values.update(str(value).strip() for value in latest_ranking["as_of_date"].dropna().unique())
    if manifest_present:
        manifest_as_of_date, _ = _parse_as_of_date(manifest.get("as_of_date"))
        if manifest_as_of_date:
            as_of_values.add(manifest_as_of_date)
    if len(as_of_values) > 1:
        errors.append(f"release outputs have inconsistent as_of_date values: {sorted(as_of_values)}")

    if live_pool_mode and legacy_mode and live_pool_mode != legacy_mode:
        errors.append("live_pool.json mode does not match live_pool_legacy.json mode")
    if live_pool_version and legacy_version and live_pool_version != legacy_version:
        errors.append("live_pool.json version does not match live_pool_legacy.json version")
    if live_pool_source_project and legacy_source_project and live_pool_source_project != legacy_source_project:
        errors.append("live_pool.json source_project does not match live_pool_legacy.json source_project")

    if expected_mode and live_pool_mode and live_pool_mode != str(expected_mode):
        errors.append(f"live_pool.json mode mismatch: expected {expected_mode} got {live_pool_mode}")
    if expected_source_project and live_pool_source_project and live_pool_source_project != str(expected_source_project):
        errors.append(
            f"live_pool.json source_project mismatch: expected {expected_source_project} got {live_pool_source_project}"
        )
    if expected_pool_size is not None and live_pool_size is not None and live_pool_size != int(expected_pool_size):
        errors.append(
            f"live_pool.json pool_size mismatch: expected {int(expected_pool_size)} got {live_pool_size}"
        )

    missing_ranking_columns = [column for column in REQUIRED_RANKING_COLUMNS if column not in latest_ranking.columns]
    if missing_ranking_columns:
        errors.append(f"latest_ranking.csv missing columns: {missing_ranking_columns}")
    elif latest_ranking.empty:
        errors.append("latest_ranking.csv must contain at least one row")
    else:
        ranking_symbols = _normalize_symbol_list(
            latest_ranking["symbol"].tolist(),
            "latest_ranking.csv symbol",
            errors,
        )
        ranking_as_of_values = sorted(str(value).strip() for value in latest_ranking["as_of_date"].dropna().unique())
        if len(ranking_as_of_values) != 1:
            errors.append(f"latest_ranking.csv must contain exactly one as_of_date, got {ranking_as_of_values}")
        selected_mask = _coerce_selected_flag(latest_ranking["selected_flag"])
        selected_symbols = set(
            _normalize_symbol_list(
                latest_ranking.loc[selected_mask, "symbol"].tolist(),
                "latest_ranking.csv selected_flag symbols",
                errors,
            )
        )
        if live_pool_symbols and not set(live_pool_symbols).issubset(set(ranking_symbols)):
            errors.append("live_pool.json symbols must all be present in latest_ranking.csv")
        if live_pool_symbols and not set(live_pool_symbols).issubset(selected_symbols):
            errors.append("live_pool.json symbols must all be selected in latest_ranking.csv")

    if manifest_present:
        manifest_mode = str(manifest.get("mode", "")).strip()
        manifest_version = str(manifest.get("version", "")).strip()
        if manifest_mode and live_pool_mode and manifest_mode != live_pool_mode:
            errors.append("release_manifest.json mode does not match live_pool.json mode")
        if manifest_version and live_pool_version and manifest_version != live_pool_version:
            errors.append("release_manifest.json version does not match live_pool.json version")
        manifest_as_of_date, _ = _parse_as_of_date(manifest.get("as_of_date"))
        if manifest_as_of_date and live_pool_as_of_date and manifest_as_of_date != live_pool_as_of_date:
            errors.append("release_manifest.json as_of_date does not match live_pool.json as_of_date")

        firestore_section = manifest.get("firestore", {})
        if not isinstance(firestore_section, dict):
            errors.append("release_manifest.json firestore must be an object")
            firestore_payload = {}
        else:
            firestore_payload = firestore_section.get("payload", {})
        if not isinstance(firestore_payload, dict):
            errors.append("release_manifest.json firestore.payload must be an object")
        else:
            firestore_symbols = firestore_payload.get("symbols")
            if firestore_symbols != live_pool_symbols:
                errors.append("release_manifest.json firestore.payload symbols do not match live_pool.json symbols")
            if firestore_payload.get("symbol_map") != legacy_symbol_map:
                errors.append(
                    "release_manifest.json firestore.payload symbol_map does not match live_pool_legacy.json symbol_map"
                )
            if str(firestore_payload.get("version", "")).strip() != live_pool_version:
                errors.append("release_manifest.json firestore.payload version does not match live_pool.json version")
            if str(firestore_payload.get("mode", "")).strip() != live_pool_mode:
                errors.append("release_manifest.json firestore.payload mode does not match live_pool.json mode")
            if str(firestore_payload.get("as_of_date", "")).strip() != live_pool_as_of_date:
                errors.append(
                    "release_manifest.json firestore.payload as_of_date does not match live_pool.json as_of_date"
                )
            try:
                firestore_pool_size = int(firestore_payload.get("pool_size", 0))
            except Exception:
                firestore_pool_size = -1
            if firestore_pool_size != len(live_pool_symbols):
                errors.append("release_manifest.json firestore.payload pool_size does not match live_pool.json")
            if str(firestore_payload.get("source_project", "")).strip() != live_pool_source_project:
                errors.append(
                    "release_manifest.json firestore.payload source_project does not match live_pool.json"
                )

    age_days: int | None = None
    if live_pool_as_of_ts is not None:
        if reference_date is None:
            reference_ts = pd.Timestamp.utcnow().normalize()
        else:
            reference_ts = pd.Timestamp(reference_date).normalize()
        age_days = (reference_ts.date() - live_pool_as_of_ts.date()).days
        if age_days < 0:
            errors.append(f"as_of_date {live_pool_as_of_date} is in the future")
        elif max_age_days is not None and age_days > int(max_age_days):
            if require_freshness:
                errors.append(
                    f"release outputs are stale by {age_days} days (max {int(max_age_days)}): {live_pool_as_of_date}"
                )
            else:
                warnings.append(
                    f"release outputs are older than {int(max_age_days)} days ({age_days} days): {live_pool_as_of_date}"
                )

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "output_dir": str(output_path),
        "manifest_present": manifest_present,
        "as_of_date": live_pool_as_of_date,
        "version": live_pool_version,
        "mode": live_pool_mode,
        "pool_size": len(live_pool_symbols),
        "symbols": live_pool_symbols,
        "source_project": live_pool_source_project,
        "age_days": age_days,
    }


def assert_release_outputs(
    output_dir: Path | str,
    **kwargs: Any,
) -> dict[str, Any]:
    validation = validate_release_outputs(output_dir, **kwargs)
    if validation["ok"]:
        return validation

    issues = [f"- {message}" for message in validation["errors"]]
    if validation["warnings"]:
        issues.append("Warnings:")
        issues.extend(f"- {message}" for message in validation["warnings"])
    raise ValueError("Release contract validation failed:\n" + "\n".join(issues))
