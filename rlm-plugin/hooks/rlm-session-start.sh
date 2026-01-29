#!/bin/bash
# RLM Session Start Hook with Mempheromone Database Loading
# Exports mempheromone context and injects a summary into session

set -euo pipefail

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")/.."
EXPORT_SCRIPT="${SCRIPT_DIR}/scripts/mempheromone_export.py"
CONTEXT_FILE="/tmp/mempheromone_context.txt"
DIGEST_FILE="/tmp/mempheromone_digest.txt"

# Run mempheromone export
EXPORT_STATS=""
if [[ -f "$EXPORT_SCRIPT" ]]; then
    EXPORT_STATS=$(python3 "$EXPORT_SCRIPT" --quiet --output "$CONTEXT_FILE" 2>/dev/null | tail -1 || echo '{}')
fi

# Parse export stats using jq if available, else grep
if command -v jq &>/dev/null; then
    MEMORIES=$(echo "$EXPORT_STATS" | jq -r '.memories // 0')
    FACTS=$(echo "$EXPORT_STATS" | jq -r '.facts // 0')
    NARRATIVES=$(echo "$EXPORT_STATS" | jq -r '.narratives // 0')
    CRYSTALLIZATIONS=$(echo "$EXPORT_STATS" | jq -r '.crystallizations // 0')
    WISDOM=$(echo "$EXPORT_STATS" | jq -r '.wisdom // 0')
    CONTEXT_SIZE=$(echo "$EXPORT_STATS" | jq -r '.output_size // 0')
else
    MEMORIES=$(echo "$EXPORT_STATS" | grep -o '"memories": [0-9]*' | grep -o '[0-9]*' || echo "0")
    FACTS=$(echo "$EXPORT_STATS" | grep -o '"facts": [0-9]*' | grep -o '[0-9]*' || echo "0")
    NARRATIVES=$(echo "$EXPORT_STATS" | grep -o '"narratives": [0-9]*' | grep -o '[0-9]*' || echo "0")
    CRYSTALLIZATIONS=$(echo "$EXPORT_STATS" | grep -o '"crystallizations": [0-9]*' | grep -o '[0-9]*' || echo "0")
    WISDOM=$(echo "$EXPORT_STATS" | grep -o '"wisdom": [0-9]*' | grep -o '[0-9]*' || echo "0")
    CONTEXT_SIZE=$(echo "$EXPORT_STATS" | grep -o '"output_size": [0-9]*' | grep -o '[0-9]*' || echo "0")
fi

# Format size for display
if [[ "$CONTEXT_SIZE" -gt 1000000 ]]; then
    SIZE_DISPLAY="$((CONTEXT_SIZE / 1000000))MB"
elif [[ "$CONTEXT_SIZE" -gt 1000 ]]; then
    SIZE_DISPLAY="$((CONTEXT_SIZE / 1000))KB"
else
    SIZE_DISPLAY="${CONTEXT_SIZE}B"
fi

# Create a digest: extract most recent/important items
if [[ -f "$CONTEXT_FILE" ]]; then
    # Extract recent session narratives and top crystallizations
    {
        echo "## MEMPHEROMONE DIGEST"
        echo "Full context: $CONTEXT_FILE ($SIZE_DISPLAY)"
        echo ""
        # Get session narratives section (first 3)
        sed -n '/## SESSION NARRATIVES/,/## [A-Z]/p' "$CONTEXT_FILE" | head -60
        echo ""
        # Get recent crystallizations (first 5)
        sed -n '/## CRYSTALLIZATIONS/,/## [A-Z]/p' "$CONTEXT_FILE" | head -40
        echo ""
        # Get top debugging facts (first 5)
        sed -n '/## DEBUGGING FACTS/,/## [A-Z]/p' "$CONTEXT_FILE" | head -50
    } > "$DIGEST_FILE" 2>/dev/null || true
fi

# Output JSON with digest embedded
DIGEST_CONTENT=""
if [[ -f "$DIGEST_FILE" ]]; then
    # Escape for JSON (replace newlines, quotes, backslashes)
    DIGEST_CONTENT=$(cat "$DIGEST_FILE" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))' | sed 's/^"//;s/"$//')
fi

cat << ENDJSON
{
  "continue": true,
  "systemMessage": "## Mempheromone Database Loaded\n\nYour memory context has been exported (${SIZE_DISPLAY}):\n- Claude Memories: ${MEMORIES}\n- Debugging Facts: ${FACTS} (score >= 10)\n- Session Narratives: ${NARRATIVES}\n- Crystallizations: ${CRYSTALLIZATIONS}\n- Wisdom: ${WISDOM}\n\nFull context file: ${CONTEXT_FILE}\n\n### RLM Available\nFor large context processing (>100K chars), use RLM:\n\`\`\`python\nfrom rlm_runner import RLMRunner\nrunner = RLMRunner()\nrunner.load('${CONTEXT_FILE}')\n\`\`\`\n\n---\n\n${DIGEST_CONTENT}"
}
ENDJSON
