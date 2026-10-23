# Contributing

Pull requests must preserve deterministic integer arithmetic in interval operations and pass the local `pytest` suite without external network dependencies.

```bash
pytest test_advisory_sweep.py -v
