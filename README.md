# SerialAdvisorySweep

Deterministic 1D interval sweep-line indexer for GenLayer Intelligent Contracts. `SerialAdvisorySweep` ingests commit-pinned hardware or firmware field bulletins, extracts affected integer serial blocks and exemption carveouts through decentralized LLM consensus, and maintains a disjoint segment tree to evaluate batch exposure in `O(S)` time.

## Technical Specification

| Parameter | Constraint / Behavior |
| :--- | :--- |
| Runtime Environment | GenVM (`py-genlayer`) |
| Consensus Mechanism | `gl.vm.run_nondet_unsafe` (exact structural coverage match + substring-grounded evidence) |
| Serial Domain | `[1, 999999]` inclusive integer coordinates |
| Max Bulletins | 12 commit-pinned JSON documents per contract instance |
| Max Intervals per Notice | 4 primary blocks, 4 carveout intervals |
| Source Integrity | SHA-256 pre-image verification on raw HTTP response bytes (`<= 12,000` bytes) |

## Interval Sweep-Line Mechanics

When a bulletin is classified as `APPLICABLE`, the contract normalizes its inclusive `[low, high]` serial blocks and subtracts any declared `carveouts`. Across all indexed bulletins, effective intervals are projected onto a 1D coordinate axis using half-open boundaries `[low, high + 1)`:

1. Entry events `(+1)` are placed at `low` and exit events `(-1)` at `high + 1`.
2. Sorting event coordinates partitions the serial space into non-overlapping contiguous slices, each associated with the exact sorted set of active bulletin IDs.
3. Adjacent slices with identical active bulletin sets are automatically coalesced.

## Public Interface

### Constructor
```python
def __init__(self, source_repo: str, vendor_name: str, product_line: str)
```
Binds the contract instance to a specific GitHub repository (`owner/repo`), hardware vendor, and product model.

### Write Methods
```python
@gl.public.write
def record_bulletin(self, source_url: str, expected_sha256: str) -> None
```
Fetches a commit-pinned JSON bulletin from `https://raw.githubusercontent.com/<source_repo>/<commit>/bulletins/<name>.json`, validates its SHA-256 digest, extracts serial coverage via LLM consensus, and recomputes the global slice partition.

### View Methods
```python
@gl.public.view
def query_batch(self, low_serial: int, high_serial: int) -> dict
```
Intersects `[low_serial, high_serial]` against the active slice partition and returns the exact count of impacted units alongside a disposition code (`CLEAR`, `PARTIALLY_IMPACTED`, `FULLY_IMPACTED`, or `NEEDS_AUDIT` if any ingested bulletin remains `UNRESOLVED`).

```python
@gl.public.view
def export_ledger(self) -> dict
```
Returns the full contract state, including target metadata, ingested bulletins, and compiled slices.

## Bulletin Document Schema

```json
{
  "id": "BULLETIN-2026-04",
  "text": "Field safety advisory for Vertex-X200 units manufactured with serial numbers 10400 through 10950 inclusive, excluding reworked units 10600 to 10649."
}
```

## Verification

Run the standalone unit test suite covering interval coalescing, carveout subtraction, sweep-line partitioning, and batch intersection:

```bash
pip install -r requirements.txt
pytest -v
```

