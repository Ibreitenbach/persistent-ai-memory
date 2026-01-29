# RLM Plugin for Mempheromone

**RLM (Reinforcement Learning Memory)** - Session awakening system that loads filtered conversation history at session start.

## Installation

```bash
# Copy plugin to Claude plugins directory
cp -r rlm-plugin ~/.claude/plugins/rlm-mempheromone
```

## What It Does

On every new Claude Code session:
1. **SessionStart hook triggers**
2. **Queries mempheromone database** for high-quality memories (pheromone >= 10)
3. **Exports ~50K tokens** of filtered history
4. **Injects into context** for instant access

**Result**: 0ms query latency - memories are already in context!

## Files

- `plugin.json` - Plugin manifest
- `hooks/rlm-session-start.sh` - Session start hook
- `scripts/mempheromone_export.py` - Memory exporter
- `scripts/mempheromone_membox.py` - Membox (topic-continuous memory)

## Configuration

Edit `scripts/mempheromone_export.py` to customize:
- Minimum pheromone score (default: 10.0)
- Maximum memories to load (default: 1000)
- Export path (default: /tmp/mempheromone_context.txt)

## Requirements

- PostgreSQL database with mempheromone schema
- Python 3.9+
- Claude Code CLI

## How It Works

```bash
# SessionStart hook runs:
python3 scripts/mempheromone_export.py \
    --min-score 10.0 \
    --max-memories 1000 \
    --output /tmp/mempheromone_context.txt

# Context is loaded into Claude's system prompt
# All subsequent queries see full filtered history
```

## See Also

- [RLM White Paper](../docs/RLM_WHITEPAPER.md) - Complete technical documentation
- [Membox Setup](../docs/MEMBOX_SETUP.md) - Topic-continuous memory integration
