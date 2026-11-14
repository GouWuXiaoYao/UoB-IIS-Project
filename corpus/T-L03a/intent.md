# Intent — T-L03a

Warehouse auditors found stock totals that drift between the report, the CSV export and the audit trail. Move the {pkg} package to integer minor units (cents), remove the process-wide caches and the ledger that grows across calls, stop evaluating discount expressions with eval, and make every consumer agree with one money contract.

## Scope

- Package: `inventory/`
- Entry point: `python app.py`
- Acceptance is decided by an unseen test suite; make the public behaviour
  described above true without changing the demo scenario in `app.py`.
