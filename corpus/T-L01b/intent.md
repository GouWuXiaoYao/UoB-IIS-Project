# Intent — T-L01b

The circulation desk reports that fine totals no longer reconcile with the ledger. Move the {pkg} package to integer minor units (cents), stop the module-level cache from accumulating across calls, and keep the report format the ledger expects.

## Scope

- Package: `loans/`
- Entry point: `python app.py`
- Acceptance is decided by an unseen test suite; make the public behaviour
  described above true without changing the demo scenario in `app.py`.
