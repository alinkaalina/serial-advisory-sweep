import json
import re
import pytest


def normalize_intervals(raw_list) -> list:
    if not isinstance(raw_list, list) or not 1 <= len(raw_list) <= 4:
        raise ValueError("Expected between 1 and 4 serial intervals")
    validated = []
    for bounds in raw_list:
        if not isinstance(bounds, list) or len(bounds) != 2:
            raise ValueError("Interval must be a [low, high] pair")
        pair = []
        for val in bounds:
            if isinstance(val, str) and re.fullmatch(r"[0-9]{1,6}", val):
                val = int(val)
            if type(val) is not int or not 1 <= val <= 999999:
                raise ValueError("Serial bound out of valid integer range")
            pair.append(val)
        if pair[0] > pair[1]:
            raise ValueError("Inverted interval bounds")
        validated.append(pair)
    coalesced = []
    for low, high in sorted(validated):
        if coalesced and low <= coalesced[-1][1] + 1:
            coalesced[-1][1] = max(coalesced[-1][1], high)
        else:
            coalesced.append([low, high])
    return coalesced


def apply_carveouts(blocks: list, carveouts: list) -> list:
    remaining = []
    for b_low, b_high in blocks:
        ptr = b_low
        for c_low, c_high in carveouts:
            if c_high < ptr or c_low > b_high:
                continue
            if ptr < c_low:
                remaining.append([ptr, c_low - 1])
            ptr = max(ptr, c_high + 1)
        if ptr <= b_high:
            remaining.append([ptr, b_high])
    return remaining


def sweep_line_partition(bulletins: list) -> list:
    deltas = {}
    for entry in bulletins:
        if entry["coverage"]["status"] != "APPLICABLE":
            continue
        effective = apply_carveouts(entry["coverage"]["blocks"], entry["coverage"]["carveouts"])
        doc_id = entry["document"]["id"]
        for low, high in effective:
            deltas.setdefault(low, []).append((doc_id, 1))
            deltas.setdefault(high + 1, []).append((doc_id, -1))

    live_set = set()
    prev_coord = None
    slices = []
    for coord in sorted(deltas):
        if prev_coord is not None and prev_coord < coord and live_set:
            active_ids = sorted(live_set)
            if slices and slices[-1]["high"] + 1 == prev_coord and slices[-1]["bulletins"] == active_ids:
                slices[-1]["high"] = coord - 1
            else:
                slices.append({"low": prev_coord, "high": coord - 1, "bulletins": active_ids})
        for doc_id, delta in deltas[coord]:
            if delta == 1:
                live_set.add(doc_id)
            else:
                live_set.remove(doc_id)
        prev_coord = coord
    return slices


def evaluate_batch_exposure(slices: list, pending_ids: list, low_serial: int, high_serial: int) -> dict:
    overlaps = [
        {
            "low": max(low_serial, s["low"]),
            "high": min(high_serial, s["high"]),
            "bulletins": s["bulletins"],
        }
        for s in slices
        if s["low"] <= high_serial and low_serial <= s["high"]
    ]
    impacted_units = sum(o["high"] - o["low"] + 1 for o in overlaps)
    batch_size = high_serial - low_serial + 1
    if pending_ids:
        disposition = "NEEDS_AUDIT"
    elif impacted_units == batch_size:
        disposition = "FULLY_IMPACTED"
    elif impacted_units > 0:
        disposition = "PARTIALLY_IMPACTED"
    else:
        disposition = "CLEAR"
    return {
        "low_serial": low_serial,
        "high_serial": high_serial,
        "disposition": disposition,
        "impacted_units": impacted_units,
        "batch_size": batch_size,
        "overlaps": overlaps,
        "unresolved_bulletins": pending_ids,
    }


def test_interval_coalescing():
    raw = [[500, 600], [100, 200], [201, 250]]
    assert normalize_intervals(raw) == [[100, 250], [500, 600]]


def test_carveout_subtraction():
    blocks = [[1000, 2000]]
    carveouts = [[1200, 1299], [1800, 2000]]
    assert apply_carveouts(blocks, carveouts) == [[1000, 1199], [1300, 1799]]


def test_sweep_line_overlapping_bulletins():
    bulletins = [
        {
            "document": {"id": "ADV-01"},
            "coverage": {"status": "APPLICABLE", "blocks": [[100, 300]], "carveouts": [[150, 199]]},
        },
        {
            "document": {"id": "ADV-02"},
            "coverage": {"status": "APPLICABLE", "blocks": [[250, 400]], "carveouts": []},
        },
    ]
    slices = sweep_line_partition(bulletins)
    assert slices == [
        {"low": 100, "high": 149, "bulletins": ["ADV-01"]},
        {"low": 200, "high": 249, "bulletins": ["ADV-01"]},
        {"low": 250, "high": 300, "bulletins": ["ADV-01", "ADV-02"]},
        {"low": 301, "high": 400, "bulletins": ["ADV-02"]},
    ]


def test_batch_exposure_dispositions():
    slices = [{"low": 100, "high": 200, "bulletins": ["ADV-01"]}]
    res_full = evaluate_batch_exposure(slices, [], 120, 180)
    assert res_full["disposition"] == "FULLY_IMPACTED"
    assert res_full["impacted_units"] == 61

    res_partial = evaluate_batch_exposure(slices, [], 50, 150)
    assert res_partial["disposition"] == "PARTIALLY_IMPACTED"
    assert res_partial["impacted_units"] == 51

    res_clear = evaluate_batch_exposure(slices, [], 300, 400)
    assert res_clear["disposition"] == "CLEAR"
    assert res_clear["impacted_units"] == 0

    res_audit = evaluate_batch_exposure(slices, ["ADV-99"], 300, 400)
    assert res_audit["disposition"] == "NEEDS_AUDIT"
