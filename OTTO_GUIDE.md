# Otto Loop Guide

The Otto loop is a portable implementation of the Ralph Wiggum Technique — an AI-assisted development methodology that uses a simple bash loop to repeatedly invoke Claude Code for iterative software development.

---

## Quick Start

```bash
# Make the script executable
chmod +x otto.sh

# Initialize git (if not already)
git init
git add -A
git commit -m "Initial commit"

# Run in build mode (unlimited iterations)
./otto.sh

# Or run a specific number of iterations
./otto.sh 10

# Run in plan mode
./otto.sh plan

# Run plan mode with max iterations
./otto.sh plan 5
```

---

## Project Structure

```
otto-matic/
├── otto.sh              # Main loop script
├── otto-init.sh        # Installation/setup script
├── PROMPT_plan.md       # Planning mode prompt
├── PROMPT_build.md      # Build mode prompt
├── AGENTS.md            # Operational guide (how to build/test)
├── IMPLEMENTATION_PLAN.md  # Prioritized task list
├── harness/            # Scenario validation harness
│   ├── scenario_harness.py  # Core harness executable
│   ├── setup_scenarios.sh   # Scenario directory setup
│   ├── requirements.txt     # Python dependencies
│   └── examples/            # Example scenario YAMLs
├── docs/plans/         # Reverse-Otto design docs (planned)
├── specs/              # Requirement specs (one per topic)
│   └── *.md            # Specification files
└── src/                # Application source code
```

---

## How the Loop Works

### Build Mode (Default)
```
./otto.sh
```
1. Reads `PROMPT_build.md`
2. Claude Code analyzes specs, picks a task from `IMPLEMENTATION_PLAN.md`
3. Implements the task using subagents
4. Runs tests (backpressure)
5. Commits and pushes
6. Exits — loop restarts with fresh context

### Plan Mode
```
./otto.sh plan
```
1. Reads `PROMPT_plan.md`
2. Analyzes gaps between specs and codebase
3. Updates `IMPLEMENTATION_PLAN.md` with prioritized tasks
4. Commits and exits

---

## Tuning Otto

### Context Efficiency

- **Token budget**: ~176K usable tokens from 200K+ context window
- **Smart zone**: 40-60% context utilization
- **One task per loop**: Maximizes context efficiency
- **Use subagents**: Each subagent gets ~156KB (memory extension)

### Steering Otto

**Upstream Steering (Setup)**
- Allocate first ~5,000 tokens for specs
- Keep every loop's context allocated with the same files
- If Otto generates wrong patterns, add/update utilities and code patterns

**Downstream Steering (Backpressure)**
- Edit `AGENTS.md` to specify your project's actual test commands
- Tests, typechecks, lints, and builds reject invalid work
- Otto will "run tests" per the prompt — make sure AGENTS.md says what to run

### Loop Parameters

| Parameter | Description | Tuning |
|-----------|-------------|--------|
| `--model MiniMax-M2.5` | Default model for build iterations | Use for most build tasks |
| `--dangerously-skip-permissions` | Auto-approve all tool calls | Use in sandbox only! |
| `MAX_ITERATIONS` | Limit iterations | Start small (5-10) to observe patterns |

### Escape Hatches

- **Ctrl+C**: Stop the loop
- **git reset --hard**: Revert uncommitted changes
- **Regenerate plan**: Delete `IMPLEMENTATION_PLAN.md` and run `./otto.sh plan`

---

## Scenario Validation Gate (Hard Invariant)

The Otto loop enforces a mandatory check between task completion and iteration exit:

```
iter N: implement → commit (exit)
        ↓ external harness runs hidden scenarios
iter N+1: read /tmp/ralph-scenario-result.json FIRST → decide: mark done OR retry
```

**The rule:** Ralph must read the scenario result at the START of each iteration before marking any task complete. If the result is `{"pass": false}`, Ralph must NOT mark tasks complete — instead continue working on the same task.

### How It Works

1. `otto.sh` waits for `/tmp/ralph-scenario-result.json` to exist before starting Ralph (via `wait_for_scenario_result()`)
2. The result is injected into `PREV_SCENARIO_RESULT` environment variable for Ralph's context
3. `PROMPT_build.md` rule `0d` instructs Ralph to check this before doing any work
4. `PROMPT_build.md` rule `999999999999999` instructs Ralph to re-check before marking tasks complete

### External Harness Responsibility

The scenario harness is integrated directly into `otto.sh` — it runs automatically after each `git push` via `sudo python3 "$HARNESS_SCRIPT" --project "$(basename "$(git rev-parse --show-toplevel)")"`.

The harness must:
- Run hidden scenario tests from `/var/otto-scenarios/[project]/` (see Security Model)
- Write `{"pass": true}` or `{"pass": false}` to `/tmp/ralph-scenario-result.json`

### Security Model

**The problem:** Ralph (Claude Code) must not be able to read scenario definitions, or it could satisfy them trivially without implementing the actual functionality.

**The solution:** File permissions + dedicated user account.

```
/var/otto-scenarios/[project]/  # root:wheel, chmod 700 — otto cannot read
/tmp/ralph-scenario-result.json  # harness writes, otto reads (world-readable)
```

- Scenario YAMLs live in `/var/otto-scenarios/[project]/*.yaml` owned by `root:wheel` with `chmod 700`
- The `otto` user cannot `ls`, `cat`, or otherwise access those files
- `otto.sh` runs Claude Code as the `otto` user via `sudo -u otto`
- The harness (running as root) runs the scenarios after each `git push` and writes the result

**Setup:**

```bash
# Create dedicatedotto user (if not exists)
sudo dscl . -create /Users/otto 2>/dev/null || true
sudo dscl . -create /Users/otto UserShell /bin/bash
sudo dscl . -create /Users/otto UniqueID 9999
sudo dscl . -create /Users/otto PrimaryGroupID 9999

# Create scenario directory with strict permissions
sudo mkdir -p /var/otto-scenarios
sudo chown root:wheel /var/otto-scenarios
sudo chmod 700 /var/otto-scenarios

# Place scenario YAMLs there (harness reads, otto cannot)
sudo mv ~/scenarios/*.yaml /var/otto-scenarios/[project]/

# Run otto — it will sudo to otto user for Claude Code
./otto.sh

# Override the run-as user if needed
RUN_AS_USER=otto ./otto.sh
```

### Verification

To test the gate works:
1. Artificially set `{"pass": false}` in the result file before running Otto
2. Observe that Ralph retries the same task instead of marking it done
3. Verify the task remains incomplete in `IMPLEMENTATION_PLAN.md`

---

## Best Practices

### When to Regenerate the Plan

Regenerate `IMPLEMENTATION_PLAN.md` when:
- Otto goes off track implementing wrong things
- The plan feels stale or doesn't match current state
- Too much clutter from completed items
- Significant spec changes
- You're confused about what's actually done

### Move Outside the Loop

- Sit and watch early to observe patterns
- Tune reactively — when Otto fails a specific way, add a sign to help next time
- "Signs" can be: prompt guardrails, AGENTS.md learnings, utilities in codebase
- The plan is disposable — regeneration cost is cheap

### Sandbox Requirements

**IMPORTANT**: Otto runs without permissions. Use a sandbox:
- **Local**: Docker container
- **Remote**: Fly Sprims, E2B, or similar

Never run directly on your host machine with access to:
- Browser cookies
- SSH keys
- Access tokens
- Private data

### Keep AGENTS.md Lean

- Only operational notes — how to build/run
- Status updates go in `IMPLEMENTATION_PLAN.md`
- A bloated AGENTS.md pollutes every loop's context

---

## Recommendations from the Source

### Context Is Everything
- Use main agent as scheduler, not for expensive work
- Prefer Markdown over JSON for token efficiency
- Subagents are memory extensions

### Let Otto Ralph
- Trust Otto to self-identify, self-correct, self-improve
- Eventual consistency through iteration
- Minimal intervention from you

### Scope Discipline
- One task per loop iteration
- Commit when tests pass
- Exit after commit — loop restarts fresh

---

## Customizing for Your Project

1. **Edit `specs/`**: Add your requirement specifications
2. **Edit `AGENTS.md`**: Fill in actual build/test commands for your project
3. **Edit `src/`**: Your application code goes here (no subdirectories required)
4. **Run `./otto.sh plan`**: Generate initial implementation plan
5. **Run `./otto.sh`**: Start building!

---

## Troubleshooting

> **Note:** Reverse-Otto (AI generating specs from code) is planned but not yet implemented. See `docs/plans/` for design documents.

| Issue | Solution |
|-------|----------|
| Otto goes in circles | Regenerate plan: `rm IMPLEMENTATION_PLAN.md && ./otto.sh plan` |
| Wrong things being built | Update specs/* and regenerate plan |
| Tests never pass | Fix AGENTS.md test commands, or fix the code |
| Context getting too full | Subagents — don't do expensive work in main agent |
