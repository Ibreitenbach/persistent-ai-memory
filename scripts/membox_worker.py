#!/usr/bin/env python3
"""
Membox Background Worker

Processes recent memories into topic-continuous memory boxes.
Designed to run as cron job or systemd service.

Usage:
    # Process last hour
    python3 membox_worker.py --since 1h

    # Process last 24 hours
    python3 membox_worker.py --since 24h

    # Process specific count
    python3 membox_worker.py --limit 100

    # Dry run
    python3 membox_worker.py --since 1h --dry-run
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / '.claude/plugins/rlm-prototype/scripts'))

from mempheromone_membox import (
    MemboxBuilder,
    get_connection,
    RealDictCursor
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_time_span(time_str: str) -> timedelta:
    """Parse time span like '1h', '24h', '7d' to timedelta."""
    if not time_str:
        return timedelta(hours=1)

    unit = time_str[-1].lower()
    value = int(time_str[:-1])

    if unit == 'h':
        return timedelta(hours=value)
    elif unit == 'd':
        return timedelta(days=value)
    elif unit == 'm':
        return timedelta(minutes=value)
    else:
        raise ValueError(f"Unknown time unit: {unit} (use h/d/m)")


def get_recent_unboxed_memories(since: timedelta, limit: int = 1000, memory_types: list = None):
    """
    Get recent memories that haven't been added to membox yet.

    Args:
        since: Time window (e.g., timedelta(hours=1))
        limit: Max memories to process
        memory_types: List of memory types to process

    Returns:
        List of dicts with memory info
    """
    memory_types = memory_types or ['debugging_fact', 'claude_memory', 'crystallization']
    cutoff_time = datetime.now() - since

    memories = []

    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            for memory_type in memory_types:
                # Query depends on memory type
                if memory_type == 'debugging_fact':
                    query = """
                        SELECT
                            df.fact_id as id,
                            df.symptom || ': ' || df.solution as content,
                            df.first_seen as created_at,
                            'debugging_fact' as memory_type
                        FROM debugging_facts df
                        LEFT JOIN memory_box_items mbi
                            ON df.fact_id = mbi.memory_id AND mbi.memory_type = 'debugging_fact'
                        WHERE df.first_seen >= %s
                          AND mbi.box_id IS NULL
                        ORDER BY df.first_seen DESC
                        LIMIT %s
                    """
                    cur.execute(query, (cutoff_time, limit))

                elif memory_type == 'claude_memory':
                    query = """
                        SELECT
                            cm.id,
                            cm.content,
                            cm.created_at,
                            'claude_memory' as memory_type
                        FROM claude_memories cm
                        LEFT JOIN memory_box_items mbi
                            ON cm.id = mbi.memory_id AND mbi.memory_type = 'claude_memory'
                        WHERE cm.created_at >= %s
                          AND mbi.box_id IS NULL
                        ORDER BY cm.created_at DESC
                        LIMIT %s
                    """
                    cur.execute(query, (cutoff_time, limit))

                elif memory_type == 'crystallization':
                    query = """
                        SELECT
                            ce.id,
                            COALESCE(ce.understanding_as_crystallized, ce.resolving_content) as content,
                            ce.created_at,
                            'crystallization' as memory_type
                        FROM crystallization_events ce
                        LEFT JOIN memory_box_items mbi
                            ON ce.id = mbi.memory_id AND mbi.memory_type = 'crystallization'
                        WHERE ce.created_at >= %s
                          AND mbi.box_id IS NULL
                        ORDER BY ce.created_at DESC
                        LIMIT %s
                    """
                    cur.execute(query, (cutoff_time, limit))

                else:
                    logger.warning(f"Unknown memory type: {memory_type}")
                    continue

                memories.extend(cur.fetchall())

    return memories


def process_memories_into_membox(
    since: timedelta = None,
    limit: int = 1000,
    memory_types: list = None,
    dry_run: bool = False
):
    """
    Process recent memories into membox.

    Args:
        since: Time window (default: 1 hour)
        limit: Max memories per type
        memory_types: Types to process
        dry_run: Preview only, don't actually process

    Returns:
        Dict with processing stats
    """
    since = since or timedelta(hours=1)
    memory_types = memory_types or ['debugging_fact', 'claude_memory', 'crystallization']

    logger.info(f"Processing memories from last {since}")
    logger.info(f"Memory types: {memory_types}")
    logger.info(f"Dry run: {dry_run}")

    # Get unboxed memories
    memories = get_recent_unboxed_memories(since, limit, memory_types)

    if not memories:
        logger.info("No new memories to process")
        return {
            'found': 0,
            'processed': 0,
            'boxes_created': 0,
            'boxes_updated': 0,
            'errors': 0
        }

    logger.info(f"Found {len(memories)} unboxed memories")

    if dry_run:
        logger.info("DRY RUN - would process:")
        for mem in memories[:10]:
            logger.info(f"  [{mem['memory_type']}] {mem['content'][:60]}...")
        if len(memories) > 10:
            logger.info(f"  ... and {len(memories) - 10} more")
        return {
            'found': len(memories),
            'processed': 0,
            'boxes_created': 0,
            'boxes_updated': 0,
            'errors': 0
        }

    # Process memories
    builder = MemboxBuilder()

    stats = {
        'found': len(memories),
        'processed': 0,
        'boxes_created': 0,
        'boxes_updated': 0,
        'errors': 0
    }

    for mem in memories:
        try:
            box = builder.add_memory(
                memory_type=mem['memory_type'],
                memory_id=mem['id'],
                content=mem['content'],
                timestamp=mem['created_at']
            )

            stats['processed'] += 1

            # Track if new box was created
            # (heuristic: if box has only 1 memory, it was just created)
            if box.memory_count == 1:
                stats['boxes_created'] += 1
            else:
                stats['boxes_updated'] += 1

            if stats['processed'] % 10 == 0:
                logger.info(f"Progress: {stats['processed']}/{len(memories)} memories processed")

        except Exception as e:
            stats['errors'] += 1
            logger.error(f"Error processing {mem['memory_type']} {mem['id']}: {e}")

    return stats


def main():
    parser = argparse.ArgumentParser(description='Membox Background Worker')
    parser.add_argument('--since', default='1h',
                       help='Time window to process (e.g., 1h, 24h, 7d)')
    parser.add_argument('--limit', type=int, default=1000,
                       help='Max memories per type (default: 1000)')
    parser.add_argument('--types', nargs='+',
                       default=['debugging_fact', 'claude_memory', 'crystallization'],
                       help='Memory types to process')
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview without processing')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose logging')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Parse time span
    try:
        since = parse_time_span(args.since)
    except ValueError as e:
        logger.error(f"Invalid time span: {e}")
        return 1

    # Process memories
    logger.info("="*60)
    logger.info("Membox Worker Starting")
    logger.info("="*60)

    stats = process_memories_into_membox(
        since=since,
        limit=args.limit,
        memory_types=args.types,
        dry_run=args.dry_run
    )

    logger.info("="*60)
    logger.info("Membox Worker Complete")
    logger.info("="*60)
    logger.info(f"Found:         {stats['found']}")
    logger.info(f"Processed:     {stats['processed']}")
    logger.info(f"Boxes Created: {stats['boxes_created']}")
    logger.info(f"Boxes Updated: {stats['boxes_updated']}")
    logger.info(f"Errors:        {stats['errors']}")

    return 0 if stats['errors'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
