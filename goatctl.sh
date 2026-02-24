#!/usr/bin/env bash
# goatctl — MojoGOAT service manager
# Usage: ./goatctl.sh {start|stop|restart|status|log}

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="/xpal-data/run/mojogoat.pid"
LOG_FILE="/xpal-data/logs/mojogoat.log"
PORT="${MOJOGOAT_PORT:-5000}"
HOST="${MOJOGOAT_HOST:-0.0.0.0}"

mkdir -p "$(dirname "$PID_FILE")" "$(dirname "$LOG_FILE")"

_is_running() {
    [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null
}

_start() {
    if _is_running; then
        echo "mojogoat already running (pid $(cat "$PID_FILE"))"
        return 0
    fi
    echo "Starting MojoGOAT on port $PORT..."
    cd "$SCRIPT_DIR"
    nohup uv run python mojogoatapi.py --port "$PORT" --host "$HOST" \
        >> "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    # Wait up to 5s for the server to answer
    for i in $(seq 1 10); do
        sleep 0.5
        curl -sf "http://localhost:$PORT/api/status" > /dev/null 2>&1 && break
    done
    if _is_running; then
        echo "Started (pid $(cat "$PID_FILE"))  →  http://localhost:$PORT/api/status"
    else
        echo "ERROR: failed to start — check $LOG_FILE" >&2
        rm -f "$PID_FILE"
        return 1
    fi
}

_stop() {
    if ! _is_running; then
        echo "mojogoat is not running"
        rm -f "$PID_FILE"
        return 0
    fi
    PID="$(cat "$PID_FILE")"
    echo "Stopping mojogoat (pid $PID)..."
    kill "$PID"
    for i in $(seq 1 20); do
        _is_running || break
        sleep 0.5
    done
    if _is_running; then
        echo "Force killing..."
        kill -9 "$PID" 2>/dev/null || true
    fi
    rm -f "$PID_FILE"
    echo "Stopped"
}

_status() {
    if _is_running; then
        PID="$(cat "$PID_FILE")"
        echo "mojogoat is running (pid $PID)  →  http://localhost:$PORT"
        curl -sf "http://localhost:$PORT/api/status" \
            | python3 -c "
import sys, json
d = json.load(sys.stdin)
ag = d.get('active_goat') or {}
goats = d.get('goats', [])
print(f'  active : {ag.get(\"name\",\"—\")} / {ag.get(\"type\",\"—\")}  ({ag.get(\"goatpath\",\"\")})')
print(f'  goats  : {[g[\"name\"] for g in goats]}')
be = d.get('backends', {})
avail = [k for k,v in be.items() if v.get('available')]
print(f'  backends available: {avail}')
" 2>/dev/null || echo "  (API not yet responding)"
    else
        echo "mojogoat is not running"
    fi
}

case "${1:-}" in
    start)   _start ;;
    stop)    _stop ;;
    restart) _stop; _start ;;
    status)  _status ;;
    log)     tail -f "$LOG_FILE" ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|log}"
        exit 1
        ;;
esac
