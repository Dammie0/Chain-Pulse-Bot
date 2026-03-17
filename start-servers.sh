#!/bin/bash
while true; do
    # Start chart server if not running
    if ! pgrep -f "chart-server.py" > /dev/null; then
        python3 ~/.openclaw/workspace/chart-server.py &
        echo "Chart server started"
    fi

    # Start futures server if not running
    if ! pgrep -f "futures-server.py" > /dev/null; then
        python3 ~/.openclaw/workspace/futures-server.py &
        echo "Futures server started"
    fi

    sleep 30
done
