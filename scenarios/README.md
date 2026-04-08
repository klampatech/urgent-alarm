# Urgent Alarm - Validation Scenarios

This directory contains validation scenarios for the Otto harness testing the Urgent Alarm app.

## Scenarios Overview

| File | Test | Spec Section |
|------|------|--------------|
| `chain-full-30min.yaml` | Full 8-anchor chain for 30min buffer | Section 2, TC-01 |
| `chain-compressed-15min.yaml` | Compressed chain for 15min buffer | Section 2, TC-02 |
| `chain-minimum-3min.yaml` | Minimum chain for 3min buffer | Section 2, TC-03 |
| `chain-invalid-rejected.yaml` | Invalid chain rejection | Section 2, TC-04 |
| `parse-natural-language.yaml` | Full NL parse | Section 3, TC-01 |
| `parse-simple-countdown.yaml` | Simple countdown parse | Section 3, TC-02 |
| `parse-tomorrow.yaml` | Tomorrow date resolution | Section 3, TC-03 |
| `voice-coach-personality.yaml` | Coach voice generation | Section 10, TC-01 |
| `voice-no-nonsense.yaml` | No-nonsense voice generation | Section 10, TC-02 |
| `voice-all-personalities.yaml` | All 5 personalities | Section 10 |
| `history-record-hit.yaml` | Record hit outcome | Section 11, TC-04 |
| `history-record-miss-feedback.yaml` | Record miss with feedback | Section 11, TC-05 |
| `stats-hit-rate.yaml` | Hit rate calculation | Section 11, TC-01 |
| `reminder-full-crud.yaml` | Full CRUD workflow | Section 13 |
| `reminder-cascade-delete.yaml` | Cascade delete anchors | Section 13, TC-03 |

## Installation

Copy scenarios to the harness directory (requires sudo):

```bash
sudo mkdir -p /var/otto-scenarios/urgent-alarm
sudo cp *.yaml /var/otto-scenarios/urgent-alarm/
```

## Running

1. Start the test server:
   ```bash
   python3 src/test_server.py &
   ```

2. Run the harness:
   ```bash
   sudo python3 harness/scenario_harness.py --project urgent-alarm
   ```

3. Or test with a custom scenario directory:
   ```bash
   OTTO_SCENARIO_DIR=~/Development/urgent-alarm/scenarios python3 harness/scenario_harness.py --project urgent-alarm
   ```
