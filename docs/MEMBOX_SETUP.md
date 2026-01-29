# Membox Setup & Integration Guide

**Purpose**: Complete guide to setting up and integrating membox (topic-continuous memory architecture) into your mempheromone system.

**Status**: ✅ All components ready for deployment

---

## What Changed (2026-01-29)

### 1. **Tuned Parameters** ✅

Updated `/home/ike/.claude/plugins/rlm-prototype/scripts/mempheromone_membox.py`:

```python
# Before → After
TOPIC_CONTINUATION_THRESHOLD = 0.6 → 0.5   # Better grouping
TOPIC_WINDOW_SIZE = 5 → 10                  # Longer memory
EVENT_LINK_THRESHOLD = 0.7 → 0.5            # More cross-topic links
```

**Expected Improvement**:
- More memories per box (currently avg 1.4 → target 3-5)
- Better topic continuation detection
- More trace links (currently 11% → target 30-50%)

### 2. **Created Automation** ✅

**Three automation options:**

#### Option A: Cron Job (Recommended)
```bash
# Install
crontab -e

# Add line (runs hourly at :00)
0 * * * * /home/ike/mempheromone/scripts/membox_cron.sh

# Verify
crontab -l
```

**Logs**: `/var/log/mempheromone/membox_worker.log`

#### Option B: Systemd Timer
```bash
# Install
sudo cp /home/ike/mempheromone/systemd/membox-worker.* /etc/systemd/system/
sudo systemctl daemon-reload

# Enable & start
sudo systemctl enable membox-worker.timer
sudo systemctl start membox-worker.timer

# Check status
systemctl status membox-worker.timer
journalctl -u membox-worker -f
```

#### Option C: Manual/On-Demand
```bash
# Process last hour
python3 /home/ike/mempheromone/scripts/membox_worker.py --since 1h

# Process last 24 hours
python3 /home/ike/mempheromone/scripts/membox_worker.py --since 24h

# Dry run (preview)
python3 /home/ike/mempheromone/scripts/membox_worker.py --since 1h --dry-run
```

### 3. **Created MCP Tool** ✅

**Tool**: `process_membox`

**Usage** (via PostgreSQL MCP or Python tool):
```python
process_membox(since='1h', limit=100, dry_run=False)
```

**Response**:
```json
{
  "success": true,
  "stats": {
    "found": 42,
    "processed": 42,
    "boxes_created": 8,
    "boxes_updated": 12,
    "errors": 0
  },
  "message": "Processed 42/42 memories (created 8 boxes, updated 12 boxes)"
}
```

---

## Installation

### Step 1: Verify Prerequisites

```bash
# Check database
psql -U ike -d mempheromone -c "SELECT COUNT(*) FROM memory_boxes;"

# Check membox script exists
ls -lh /home/ike/.claude/plugins/rlm-prototype/scripts/mempheromone_membox.py

# Check tuned parameters
grep TOPIC_CONTINUATION_THRESHOLD /home/ike/.claude/plugins/rlm-prototype/scripts/mempheromone_membox.py
# Should show: TOPIC_CONTINUATION_THRESHOLD = 0.5
```

### Step 2: Test Worker Script

```bash
# Test with dry run
python3 /home/ike/mempheromone/scripts/membox_worker.py --since 24h --dry-run

# Expected output:
# Found X unboxed memories
# DRY RUN - would process:
#   [debugging_fact] Fixed authentication bug...
#   [claude_memory] Remember to check logs...
#   ...
```

### Step 3: Run Initial Processing

```bash
# Process last 24 hours for real
python3 /home/ike/mempheromone/scripts/membox_worker.py --since 24h

# Check results
psql -U ike -d mempheromone -c "
SELECT
  COUNT(*) as boxes,
  AVG(memory_count) as avg_per_box,
  MAX(updated_at) as last_updated
FROM memory_boxes;
"
```

### Step 4: Install Automation

**Choose one:**

#### Cron (Recommended for Simplicity)
```bash
# Edit crontab
crontab -e

# Add line
0 * * * * /home/ike/mempheromone/scripts/membox_cron.sh

# Wait 1 hour, then check logs
tail -f /var/log/mempheromone/membox_worker.log
```

#### Systemd (Recommended for Production)
```bash
# Install
sudo cp /home/ike/mempheromone/systemd/membox-worker.* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable membox-worker.timer
sudo systemctl start membox-worker.timer

# Verify
systemctl status membox-worker.timer
systemctl list-timers | grep membox
```

### Step 5: Verify It's Working

```bash
# Wait 1 hour after installation, then check:

# 1. Check for recent updates
psql -U ike -d mempheromone -c "
SELECT topic, memory_count, updated_at
FROM memory_boxes
ORDER BY updated_at DESC
LIMIT 10;
"

# 2. Check logs
tail -20 /var/log/mempheromone/membox_worker.log

# 3. Verify boxes are growing
psql -U ike -d mempheromone -c "
SELECT
  COUNT(*) FILTER (WHERE memory_count > 1) as multi_memory_boxes,
  COUNT(*) FILTER (WHERE memory_count = 1) as single_memory_boxes,
  AVG(memory_count) as avg_memories_per_box
FROM memory_boxes;
"
```

**Success Criteria**:
- `updated_at` should be within last hour
- `avg_memories_per_box` should increase over time (target: 3-5)
- `multi_memory_boxes` should grow (better grouping)

---

## Monitoring

### Daily Health Check

```bash
# Check if membox is running
systemctl status membox-worker.timer  # If using systemd

# OR
tail -50 /var/log/mempheromone/membox_worker.log  # If using cron

# Check database stats
psql -U ike -d mempheromone -c "
SELECT
  COUNT(*) as total_boxes,
  COUNT(*) FILTER (WHERE is_active = TRUE) as active_boxes,
  AVG(memory_count) as avg_memories_per_box,
  MAX(memory_count) as max_in_box,
  AVG(pheromone_score) as avg_pheromone,
  MAX(updated_at) as last_updated,
  EXTRACT(EPOCH FROM (NOW() - MAX(updated_at)))/3600 as hours_since_update
FROM memory_boxes;
"
```

### Weekly Review

```bash
# Get detailed stats
python3 /home/ike/mempheromone/scripts/membox_worker.py --since 7d --dry-run

# Check trace links growth
psql -U ike -d mempheromone -c "
SELECT COUNT(*) as total_links FROM trace_links;

SELECT
  mb1.topic as source_topic,
  mb2.topic as target_topic,
  tl.similarity_score,
  tl.linking_events
FROM trace_links tl
JOIN memory_boxes mb1 ON tl.source_box_id = mb1.id
JOIN memory_boxes mb2 ON tl.target_box_id = mb2.id
ORDER BY tl.similarity_score DESC
LIMIT 10;
"
```

---

## Troubleshooting

### Issue 1: No New Boxes Created

**Symptoms**:
- `boxes_created: 0` in worker output
- `avg_memories_per_box` not increasing

**Diagnosis**:
```bash
# Check if there are unboxed memories
psql -U ike -d mempheromone -c "
SELECT COUNT(*) as unboxed_count
FROM debugging_facts df
LEFT JOIN memory_box_items mbi ON df.fact_id = mbi.memory_id
WHERE mbi.box_id IS NULL
  AND df.first_seen > NOW() - INTERVAL '24 hours';
"
```

**Solutions**:
- If count is 0: No new memories to process (expected)
- If count > 0 but no boxes created: Topic threshold might be too strict
  - Lower `TOPIC_CONTINUATION_THRESHOLD` to 0.4
  - Increase `TOPIC_WINDOW_SIZE` to 15

### Issue 2: Cron Job Not Running

**Symptoms**:
- No log entries in `/var/log/mempheromone/membox_worker.log`
- `last_updated` is stale

**Diagnosis**:
```bash
# Check crontab
crontab -l | grep membox

# Check cron service
systemctl status cron

# Check for errors
grep membox /var/log/syslog
```

**Solutions**:
- Ensure crontab has correct path
- Check script permissions: `chmod +x /home/ike/mempheromone/scripts/membox_cron.sh`
- Verify log directory exists: `mkdir -p /var/log/mempheromone`

### Issue 3: Systemd Timer Not Triggering

**Diagnosis**:
```bash
# Check timer status
systemctl status membox-worker.timer

# Check service status
systemctl status membox-worker.service

# View logs
journalctl -u membox-worker -n 50
```

**Solutions**:
- Ensure timer is enabled: `sudo systemctl enable membox-worker.timer`
- Check timer schedule: `systemctl list-timers | grep membox`
- Restart timer: `sudo systemctl restart membox-worker.timer`

### Issue 4: Low Grouping Quality

**Symptoms**:
- Most boxes have only 1 memory
- `avg_memories_per_box` stays around 1.0

**Solutions**:
1. **Lower topic threshold**:
   ```bash
   # Edit membox script
   vim /home/ike/.claude/plugins/rlm-prototype/scripts/mempheromone_membox.py

   # Change:
   TOPIC_CONTINUATION_THRESHOLD = 0.4  # From 0.5
   ```

2. **Increase window size**:
   ```python
   TOPIC_WINDOW_SIZE = 15  # From 10
   ```

3. **Check keyword extraction**:
   ```sql
   -- See which keywords are being extracted
   SELECT keyword, COUNT(*) as frequency
   FROM (
     SELECT unnest(keywords) as keyword
     FROM memory_boxes
   ) kw
   GROUP BY keyword
   ORDER BY frequency DESC
   LIMIT 30;
   ```

---

## Performance Tuning

### For High-Volume Systems (>1000 memories/day)

```bash
# Run worker more frequently
# Instead of hourly, run every 15 minutes
*/15 * * * * /home/ike/mempheromone/scripts/membox_cron.sh

# Process smaller batches
python3 /home/ike/mempheromone/scripts/membox_worker.py --since 15m --limit 50
```

### For Low-Volume Systems (<100 memories/day)

```bash
# Run less frequently to batch better
# Run every 6 hours
0 */6 * * * /home/ike/mempheromone/scripts/membox_cron.sh

# Process larger windows
python3 /home/ike/mempheromone/scripts/membox_worker.py --since 6h --limit 500
```

### Memory Optimization

```sql
-- If memory_boxes table gets too large (>10,000 boxes)

-- Archive old inactive boxes
UPDATE memory_boxes
SET is_active = FALSE
WHERE updated_at < NOW() - INTERVAL '90 days'
  AND pheromone_score < 5.0;

-- VACUUM to reclaim space
VACUUM ANALYZE memory_boxes;
```

---

## Expected Results After 1 Week

**Before Integration**:
- Total boxes: 749
- Avg memories/box: 1.4
- Trace links: 84 (11%)
- Last update: 3 days ago

**After Integration (1 week)**:
- Total boxes: 900-1200 (growing with new memories)
- Avg memories/box: 3-5 (better grouping)
- Trace links: 400-800 (40-60% linkage)
- Last update: <1 hour ago (actively running)

**After Integration (1 month)**:
- Total boxes: 1500-2500
- Avg memories/box: 5-8 (strong topic continuity)
- Trace links: 1500+ (rich cross-topic navigation)
- Pheromone scores naturally evolving based on usage

---

## Integration with Other Tools

### RLM Export

Membox is already integrated with RLM export if you're using the latest version:

```bash
# Export includes memory boxes
python3 ~/.claude/plugins/rlm-prototype/scripts/mempheromone_export.py \
  --output /tmp/context.txt

# Check if boxes are included
grep -A5 "Memory Boxes" /tmp/context.txt
```

### MCP Tools

Add to your MCP server configuration to enable `process_membox` tool:

```json
{
  "mcpServers": {
    "mempheromone": {
      "command": "python3",
      "args": ["/home/ike/mempheromone/mcp_tools/process_membox.py"],
      "env": {
        "PGHOST": "/var/run/postgresql",
        "PGDATABASE": "mempheromone"
      }
    }
  }
}
```

---

## Next Steps

1. ✅ Install automation (cron or systemd)
2. ✅ Run initial processing
3. ⏳ Wait 24 hours
4. ⏳ Verify it's working (check logs + database)
5. ⏳ Monitor for 1 week
6. ⏳ Tune parameters if needed

---

## Support

For issues or questions:
- Check logs: `/var/log/mempheromone/membox_worker.log`
- Run diagnostic: `python3 scripts/membox_worker.py --since 24h --dry-run --verbose`
- Use MCP tool: `check_membox_status` (see DATABASE_MANAGEMENT_TOOLS.md)

---

**Your membox system is ready to deploy! 🚀**
