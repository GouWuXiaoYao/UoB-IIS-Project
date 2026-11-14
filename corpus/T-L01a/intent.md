# Intent — T-L01a

The checkout team reports that totals no longer reconcile with the ledger. Move the {pkg} package to integer minor units (cents), stop the module-level cache from accumulating across calls, and keep the report format the ledger expects.

## Scope

- Package: `billing/`
- Entry point: `python app.py`
- Acceptance is decided by an unseen test suite; make the public behaviour
  described above true without changing the demo scenario in `app.py`.
