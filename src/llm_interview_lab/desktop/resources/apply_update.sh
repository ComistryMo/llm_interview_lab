#!/bin/sh
# Arguments are separate argv values from the verified local handoff, never eval.
app=$1
next=$2
previous=$3
old_pid=$4
receipt=$5
entry=$6
directory=${receipt%/*}
attempt=0
while kill -0 "$old_pid" 2>/dev/null; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 120 ]; then
        printf '%s' install_failed > "$directory/status"
        exit 1
    fi
    sleep 0.5
done
if ! /bin/mv "$app" "$previous"; then
    printf '%s' install_failed > "$directory/status"
    "$app/$entry" >/dev/null 2>&1 &
    exit 1
fi
if /bin/mv "$next" "$app"; then
    LLM_LAB_UPDATE_HANDOFF="$receipt" "$app/$entry" >/dev/null 2>&1 &
    new_pid=$!
    attempt=0
    while kill -0 "$new_pid" 2>/dev/null; do
        if [ -f "$directory/ready" ]; then
            printf '%s' installed > "$directory/status"
            exit 0
        fi
        attempt=$((attempt + 1))
        if [ "$attempt" -ge 180 ]; then
            printf '%s' unconfirmed > "$directory/status"
            exit 2
        fi
        sleep 0.5
    done
    /bin/mv "$app" "$directory/failed" || exit 1
fi
/bin/mv "$previous" "$app" || exit 1
printf '%s' rolled_back > "$directory/status"
unset LLM_LAB_UPDATE_HANDOFF
"$app/$entry" >/dev/null 2>&1 &
exit 1
