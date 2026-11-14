# Intent — T-L02a

Support reports that box-office totals disagree with the finance export. Move the {pkg} package to integer minor units (cents), stop the module-level cache from accumulating across calls, and make the report and the CSV export agree with the same money contract.

## Scope

- Package: `ticketing/`
- Entry point: `python app.py`
- Acceptance is decided by an unseen test suite; make the public behaviour
  described above true without changing the demo scenario in `app.py`.
