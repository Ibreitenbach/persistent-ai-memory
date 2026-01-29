#!/bin/bash
#
# Membox Cron Job
#
# Processes recent memories into topic-continuous boxes.
# Run every hour to keep membox up-to-date.
#
# Installation:
#   crontab -e
#   Add: 0 * * * * /home/ike/mempheromone/scripts/membox_cron.sh
#

# Configuration
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
LOG_DIR="/var/log/mempheromone"
LOG_FILE="${LOG_DIR}/membox_worker.log"
WORKER_SCRIPT="${SCRIPT_DIR}/membox_worker.py"

# Ensure log directory exists
mkdir -p "${LOG_DIR}" 2>/dev/null

# Log rotation - keep last 7 days
if [ -f "${LOG_FILE}" ]; then
    # If log file is older than 7 days, rotate it
    find "${LOG_DIR}" -name "membox_worker.log.*" -mtime +7 -delete

    # If current log is > 10MB, rotate it
    if [ $(stat -f%z "${LOG_FILE}" 2>/dev/null || stat -c%s "${LOG_FILE}") -gt 10485760 ]; then
        mv "${LOG_FILE}" "${LOG_FILE}.$(date +%Y%m%d-%H%M%S)"
    fi
fi

# Run membox worker
{
    echo "========================================="
    echo "Membox Cron Job - $(date)"
    echo "========================================="

    python3 "${WORKER_SCRIPT}" --since 1h

    EXIT_CODE=$?

    echo "Exit code: ${EXIT_CODE}"
    echo ""
} >> "${LOG_FILE}" 2>&1

exit ${EXIT_CODE}
