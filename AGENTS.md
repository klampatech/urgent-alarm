## Build & Run

Succinct rules for how to BUILD the project:

## Validation

Run these after implementing to get immediate feedback:

- Tests: `python3 -m pytest harness/` (or manual harness test)
- Typecheck: Not required for Python
- Lint: `python3 -m py_compile harness/scenario_harness.py src/web.py`

## Operational Notes

Succinct learnings about how to RUN the project:

### Starting the demo server
```bash
python3 src/web.py &
```

### Running the harness manually
```bash
sudo python3 harness/scenario_harness.py --project otto-matic
```

### Creating scenarios (requires sudo)
```bash
sudo mkdir -p /var/otto-scenarios/otto-matic
sudo cp my-scenarios/*.yaml /var/otto-scenarios/otto-matic/
```

### Codebase Patterns

...
