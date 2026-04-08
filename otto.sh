#!/bin/bash
# Otto - The Ralph Wiggum Technique for AI-assisted development
#
# Usage: ./otto.sh [options] [plan|max_iterations]
# Options:
#   --agent <name>    Coding agent to use: claude (default) or pi
# Examples:
#   ./otto.sh              # Build mode, unlimited iterations (uses claude)
#   ./otto.sh --agent pi   # Build mode using pi coding agent
#   ./otto.sh 20           # Build mode, max 20 iterations
#   ./otto.sh plan         # Plan mode, unlimited iterations
#   ./otto.sh plan 5       # Plan mode, max 5 iterations
#   ./otto.sh --agent pi plan 5  # Plan mode with pi, max 5 iterations

# Spinner animation for streaming mode
spinner_pid=""
show_spinner=false

start_spinner() {
    show_spinner=true
    local delay=0.1
    local spinchars='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    local i=0

    # Run in background, output to stderr to not interfere with main output
    (
        while [ "$show_spinner" = true ]; do
            local char="${spinchars:$((i % ${#spinchars})):1}"
            echo -ne "\r\033[K  🦦 \033[1;36m$char\033[0m " >&2
            sleep $delay
            i=$((i + 1))
        done
        # Clear the spinner line when done
        echo -ne "\r\033[K" >&2
    ) &
    spinner_pid=$!
}

stop_spinner() {
    show_spinner=false
    if [ -n "$spinner_pid" ]; then
        kill "$spinner_pid" 2>/dev/null || true
        wait $spinner_pid 2>/dev/null || true
        spinner_pid=""
    fi
    # Ensure clean line
    echo -ne "\r\033[K" >&2
}

# Cleanup function for Ctrl+C
cleanup() {
    echo -e "\n\n⚠️  Interrupted. Cleaning up..."
    stop_spinner
    exit 130
}

# Trap Ctrl+C (SIGINT)
trap cleanup SIGINT

# Default agent (can be overridden with --agent flag)
AGENT="claude"

# Parse arguments
MODE="build"
PROMPT_FILE="PROMPT_build.md"
MAX_ITERATIONS=0

while [[ $# -gt 0 ]]; do
    case $1 in
        --agent)
            AGENT="$2"
            shift 2
            ;;
        plan)
            MODE="plan"
            PROMPT_FILE="PROMPT_plan.md"
            shift
            ;;
        *)
            if [[ "$1" =~ ^[0-9]+$ ]]; then
                MAX_ITERATIONS="$1"
            fi
            shift
            ;;
    esac
done

ITERATION=0
CURRENT_BRANCH=$(git branch --show-current)
LAST_PLAN_HASH=""
SCENARIO_RESULT_FILE="/tmp/ralph-scenario-result.json"

# User to run agents as (must not be able to read scenario files)
# The Otto user should NOT be sudo NOPASSWD — only this script can sudo to it
RUN_AS_USER="${RUN_AS_USER:-otto}"

# Check if target user exists, fall back to current user if not
if ! id "$RUN_AS_USER" &>/dev/null; then
    echo "  ⚠️  User '$RUN_AS_USER' not found, using current user ($USER)"
    RUN_AS_USER="$USER"
fi

# Harness script path
HARNESS_SCRIPT="${HARNESS_SCRIPT:-$(dirname "$0")/harness/scenario_harness.py}"

# Test server configuration (optional - set TEST_SERVER_SCRIPT to enable)
TEST_SERVER_PORT="${TEST_SERVER_PORT:-8090}"
TEST_SERVER_SCRIPT="${TEST_SERVER_SCRIPT:-}"

# Ensure test server is running (only if TEST_SERVER_SCRIPT is set)
ensure_test_server() {
    # Skip if not configured
    [ -z "$TEST_SERVER_SCRIPT" ] && return 0
    
    local port="$TEST_SERVER_PORT"
    local max_wait=30
    local waited=0
    
    # Check if server is already running
    if curl -s -o /dev/null -w "%{http_code}" "http://localhost:$port/health" 2>/dev/null | grep -q "200"; then
        echo "  ✅ Test server already running on port $port"
        return 0
    fi
    
    echo "  ⏳ Test server not running on port $port"
    
    # Check if server script exists
    if [ ! -f "$TEST_SERVER_SCRIPT" ]; then
        echo "  ⚠️  Test server script not found: $TEST_SERVER_SCRIPT"
        return 1
    fi
    
    # Start the server in background
    echo "  🚀 Starting test server..."
    python3 "$TEST_SERVER_SCRIPT" &
    local server_pid=$!
    
    # Wait for server to be ready
    while [ $waited -lt $max_wait ]; do
        if curl -s -o /dev/null -w "%{http_code}" "http://localhost:$port/health" 2>/dev/null | grep -q "200"; then
            echo "  ✅ Test server started (PID: $server_pid) on port $port"
            return 0
        fi
        sleep 1
        waited=$((waited + 1))
    done
    
    echo "  ⚠️  Test server failed to start within ${max_wait}s"
    return 1
}

# Run a command as RUN_AS_USER
run_as_otto() {
    sudo -u "$RUN_AS_USER" "$@"
}

# Wait for scenario result file from previous iteration (if any)
wait_for_scenario_result() {
    # Only wait if this isn't the first iteration (i.e., result file might exist from prior run)
    if [ $ITERATION -gt 0 ]; then
        echo "  ⏳ Waiting for scenario result from previous iteration..."
        local max_wait=300  # 5 minute max wait
        local waited=0
        while [ ! -f "$SCENARIO_RESULT_FILE" ] && [ $waited -lt $max_wait ]; do
            sleep 1
            waited=$((waited + 1))
        done
        if [ ! -f "$SCENARIO_RESULT_FILE" ]; then
            echo "  ⚠️  Scenario result not found after ${max_wait}s, continuing anyway"
        else
            echo "  ✅ Scenario result found"
        fi
    fi
}

# Plan mode exit conditions
check_plan_exit() {
    if [ "$MODE" != "plan" ]; then
        return 1
    fi

    # Exit if specs/ is empty or doesn't exist
    if [ ! -d "specs" ] || [ -z "$(ls -A specs/ 2>/dev/null)" ]; then
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "Plan mode: No specs found in specs/"
        echo "Exiting loop."
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        return 0
    fi

    # Exit if IMPLEMENTATION_PLAN.md hasn't changed (stable)
    if [ -f "IMPLEMENTATION_PLAN.md" ]; then
        # Use md5 of working directory file (not git object)
        CURRENT_HASH=$(md5 -q IMPLEMENTATION_PLAN.md)
        if [ -n "$LAST_PLAN_HASH" ] && [ "$CURRENT_HASH" = "$LAST_PLAN_HASH" ]; then
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo "Plan mode: Plan is stable (no changes)"
            echo "Exiting loop."
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            return 0
        fi
        LAST_PLAN_HASH="$CURRENT_HASH"
    fi

    return 1
}

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Otto Loop"
echo "Agent:  $AGENT"
echo "Mode:   $MODE"
echo "Prompt: $PROMPT_FILE"
echo "Branch: $CURRENT_BRANCH"
[ $MAX_ITERATIONS -gt 0 ] && echo "Max:    $MAX_ITERATIONS iterations"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Verify prompt file exists
if [ ! -f "$PROMPT_FILE" ]; then
    echo "Error: $PROMPT_FILE not found"
    exit 1
fi

while true; do
    # Check plan mode exit conditions (exits loop if plan is stable)
    if check_plan_exit; then
        break
    fi

    # Wait for scenario result only in build mode (harness creates the result file)
    if [ "$MODE" = "build" ]; then
        wait_for_scenario_result
    fi

    if [ $MAX_ITERATIONS -gt 0 ] && [ $ITERATION -ge $MAX_ITERATIONS ]; then
        echo "Reached max iterations: $MAX_ITERATIONS"
        break
    fi

    # Run Otto iteration with selected prompt
    start_spinner

    # Load previous scenario result if available for Ralph context
    if [ -f "$SCENARIO_RESULT_FILE" ]; then
        export PREV_SCENARIO_RESULT=$(cat "$SCENARIO_RESULT_FILE")
    else
        export PREV_SCENARIO_RESULT=""
    fi

    # Temp file for agent output
    temp_output=$(mktemp)
    chmod 666 "$temp_output"

    # Create temp file with prompt (both agents use @filepath syntax)
    temp_prompt=$(mktemp)
    chmod 666 "$temp_prompt"
    cat "$PROMPT_FILE" > "$temp_prompt"

    if [ "$AGENT" = "pi" ]; then
        # pi outputs JSON Lines with event objects
        PREV_SCENARIO_RESULT="${PREV_SCENARIO_RESULT:-}" \
            pi -p --mode json --no-extensions "@$temp_prompt" > "$temp_output"
    else
        # Claude Code - use native JSON output
        PREV_SCENARIO_RESULT="${PREV_SCENARIO_RESULT:-}" \
            claude -p \
            "@$temp_prompt" \
            --dangerously-skip-permissions \
            --output-format=json \
            --model MiniMax-M2.5 \
            2>/dev/null > "$temp_output"
    fi

    rm -f "$temp_prompt"

    stop_spinner

    # Parse and display JSON output with nice formatting
    if command -v jq &> /dev/null; then
        # Check if we have valid JSON with result field
        if jq -e '.result' "$temp_output" >/dev/null 2>&1; then
            # Show main text response
            result_text=$(jq -r '.result' "$temp_output")
            echo ""
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo "  💬 Response"
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo "$result_text"
            echo ""

            # Show tool calls from iterations if any
            if jq -e '.iterations[]' "$temp_output" >/dev/null 2>&1; then
                echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                echo "  🔧 Tool Calls"
                echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

                jq -r '.iterations[]? | to_entries[] | select(.key == "tool") | .value[]? | to_entries[] | select(.key == "name" or .key == "input") | "\(.key): \(.value)"' "$temp_output" 2>/dev/null | while read -r line; do
                    echo "  $line"
                done
            fi
        else
            # Fallback: show raw output if parsing fails
            cat "$temp_output"
        fi
    else
        # No jq, show raw output
        cat "$temp_output"
    fi

    # Also save raw JSON to log file for debugging
    echo "=== Iteration $ITERATION ===" >> otto.log
    cat "$temp_output" >> otto.log
    echo "" >> otto.log

    rm -f "$temp_output"

    # Push changes after each iteration (skip if no remote configured)
    if git remote get-url origin &>/dev/null; then
        echo "  Pushing to remote..."
        git push origin "$CURRENT_BRANCH" || {
            echo "Failed to push. Creating remote branch..."
            git push -u origin "$CURRENT_BRANCH"
        }
    else
        echo "  ⚠️  No git remote configured, skipping push"
    fi

    # Run scenario harness only in build mode
    # In plan mode, we only analyze - no code to test
    if [ "$MODE" = "build" ]; then
        # Ensure test server is running (if configured via TEST_SERVER_SCRIPT env var)
        ensure_test_server
        
        echo "  Running scenario harness..."
        sudo python3 "$HARNESS_SCRIPT" --project "$(basename "$(git rev-parse --show-toplevel)")" || {
            # If harness fails to run, write failure result
            echo '{"pass": false}' > /tmp/ralph-scenario-result.json
        }
    fi

    ITERATION=$((ITERATION + 1))

    # Show iteration banner (don't clear - keep previous output visible for debugging)
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Otto Loop"
    echo "  Iteration: $ITERATION"
    [ $MAX_ITERATIONS -gt 0 ] && echo "  Max: $MAX_ITERATIONS"
    echo "  Branch: $CURRENT_BRANCH"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
done
