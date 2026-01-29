#!/usr/bin/env python3
"""
Mempheromone Database Export for RLM Session Loading

Exports high-value memory data from mempheromone PostgreSQL database
for injection into Claude Code sessions via RLM.

Tables exported (prioritized by value):
1. claude_memories - Personal learnings and insights
2. debugging_facts - Top-scored problem/solution pairs
3. session_narratives - Session summaries and arcs
4. crystallization_events - WYKYK moments
5. wisdom - Crystallized understandings
6. chatroom_turns - Recent collaboration context
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("Installing psycopg2-binary...")
    os.system(f"{sys.executable} -m pip install psycopg2-binary -q")
    import psycopg2
    import psycopg2.extras


def get_connection():
    """Get database connection using standard mempheromone config."""
    return psycopg2.connect(
        host=os.environ.get('PGHOST', 'localhost'),
        port=os.environ.get('PGPORT', '5432'),
        database=os.environ.get('PGDATABASE', 'mempheromone'),
        user=os.environ.get('PGUSER', 'ike'),
        password=os.environ.get('PGPASSWORD', '')
    )


def export_claude_memories(conn, limit=500):
    """Export Claude's personal memories (insights, learnings, decisions)."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT memory_type, topic, content, context, confidence, created_at
            FROM claude_memories
            ORDER BY created_at DESC
            LIMIT %s
        """, (limit,))
        return cur.fetchall()


def export_debugging_facts(conn, min_score=10, limit=500):
    """Export high-scoring debugging facts (problem/solution pairs)."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT symptom, solution, pheromone_score,
                   verified_count, outcome, source, first_seen
            FROM debugging_facts
            WHERE pheromone_score >= %s AND is_archived = false
            ORDER BY pheromone_score DESC, verified_count DESC
            LIMIT %s
        """, (min_score, limit))
        return cur.fetchall()


def export_session_narratives(conn, limit=50):
    """Export recent session narratives (summaries of past sessions)."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT session_id, start_state, end_state, narrative_arc,
                   affective_shape, topics, created_at
            FROM session_narratives
            ORDER BY created_at DESC
            LIMIT %s
        """, (limit,))
        return cur.fetchall()


def export_crystallizations(conn, limit=200):
    """Export WYKYK crystallization events."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT certainty_type, understanding_as_crystallized, what_changed,
                   question_as_held, temperature, amplitude, created_at
            FROM crystallization_events
            WHERE certainty_type IN ('WYKYK', 'PROBABLE')
            ORDER BY created_at DESC
            LIMIT %s
        """, (limit,))
        return cur.fetchall()


def export_wisdom(conn, limit=300):
    """Export crystallized wisdom entries."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT insight, context, discovered_by, confidence,
                   times_applied, domain, created_at
            FROM wisdom
            ORDER BY times_applied DESC, confidence DESC
            LIMIT %s
        """, (limit,))
        return cur.fetchall()


def export_recent_chat(conn, days=7, limit=200):
    """Export recent chatroom turns for collaboration context."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cutoff = datetime.now() - timedelta(days=days)
        cur.execute("""
            SELECT participant, content, created_at
            FROM chatroom_turns
            WHERE created_at > %s
            ORDER BY created_at DESC
            LIMIT %s
        """, (cutoff, limit))
        return cur.fetchall()


def export_exocortex_memories(conn, limit=200):
    """Export high-quality exocortex memories."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT source_table, content, pheromone_weight, created_at
            FROM exocortex_memory_bank
            WHERE pheromone_weight >= 8
            ORDER BY pheromone_weight DESC
            LIMIT %s
        """, (limit,))
        return cur.fetchall()


def export_memory_boxes(conn, limit=50, min_score=8.0):
    """Export topic-continuous memory boxes with trace links."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        # Get top memory boxes
        cur.execute("""
            SELECT mb.id, mb.topic, mb.keywords, mb.events, mb.summary,
                   mb.memory_count, mb.pheromone_score, mb.start_time, mb.end_time
            FROM memory_boxes mb
            WHERE mb.is_active = TRUE AND mb.pheromone_score >= %s
            ORDER BY mb.pheromone_score DESC, mb.memory_count DESC
            LIMIT %s
        """, (min_score, limit))
        boxes = cur.fetchall()

        # Get trace links for navigation
        cur.execute("""
            SELECT tl.source_box_id, tl.target_box_id, tl.link_type,
                   tl.similarity_score, tl.linking_events,
                   mb.topic as target_topic
            FROM trace_links tl
            JOIN memory_boxes mb ON mb.id = tl.target_box_id
            WHERE tl.similarity_score >= 0.5
            ORDER BY tl.similarity_score DESC
            LIMIT 100
        """)
        links = cur.fetchall()

        return {'boxes': boxes, 'links': links}


def format_for_rlm(data: dict) -> str:
    """Format exported data as structured text for RLM context."""
    lines = []

    lines.append("=" * 80)
    lines.append("MEMPHEROMONE DATABASE CONTEXT")
    lines.append(f"Exported: {datetime.now().isoformat()}")
    lines.append("=" * 80)

    # Claude Memories
    if data.get('memories'):
        lines.append("\n## CLAUDE MEMORIES (Personal Learnings)")
        lines.append("-" * 60)
        for m in data['memories']:
            lines.append(f"\n### [{m['memory_type'].upper()}] {m['topic']}")
            lines.append(f"Content: {m['content']}")
            if m.get('context'):
                lines.append(f"Context: {m['context']}")
            lines.append(f"Confidence: {m.get('confidence', 'N/A')}")

    # Debugging Facts
    if data.get('facts'):
        lines.append("\n\n## DEBUGGING FACTS (Proven Solutions)")
        lines.append("-" * 60)
        for f in data['facts']:
            lines.append(f"\n### Problem: {f['symptom'][:200]}")
            lines.append(f"Solution: {f['solution'][:500]}")
            score = float(f['pheromone_score']) if f.get('pheromone_score') else 0
            lines.append(f"Score: {score:.1f} | Verified: {f.get('verified_count', 0)}x | Source: {f.get('source', 'unknown')}")

    # Session Narratives
    if data.get('narratives'):
        lines.append("\n\n## SESSION NARRATIVES (Past Session Summaries)")
        lines.append("-" * 60)
        for n in data['narratives']:
            lines.append(f"\n### Session {str(n.get('session_id', 'unknown'))[:8]}")
            lines.append(f"Arc: {n.get('narrative_arc', 'unknown')} | Shape: {n.get('affective_shape', 'unknown')}")
            if n.get('start_state'):
                lines.append(f"Start: {n['start_state'][:200]}")
            if n.get('end_state'):
                lines.append(f"End: {n['end_state'][:200]}")
            if n.get('topics'):
                topics = n['topics'] if isinstance(n['topics'], list) else []
                lines.append(f"Topics: {', '.join(topics[:5])}")

    # Crystallizations
    if data.get('crystallizations'):
        lines.append("\n\n## CRYSTALLIZATIONS (WYKYK Moments)")
        lines.append("-" * 60)
        for c in data['crystallizations']:
            lines.append(f"\n### [{c.get('certainty_type', 'UNKNOWN')}]")
            if c.get('understanding_as_crystallized'):
                lines.append(f"Understanding: {c['understanding_as_crystallized'][:500]}")
            if c.get('what_changed'):
                lines.append(f"What changed: {c['what_changed'][:200]}")
            if c.get('question_as_held'):
                lines.append(f"Question held: {c['question_as_held'][:150]}")
            temp = c.get('temperature', 'N/A')
            amp = c.get('amplitude', 'N/A')
            lines.append(f"Temperature: {temp} | Amplitude: {amp}")

    # Wisdom
    if data.get('wisdom'):
        lines.append("\n\n## WISDOM (Crystallized Understandings)")
        lines.append("-" * 60)
        for w in data['wisdom']:
            lines.append(f"\n- {w['insight'][:300]}")
            conf = float(w['confidence']) if w.get('confidence') else 0
            lines.append(f"  (By: {w.get('discovered_by', 'unknown')} | Domain: {w.get('domain', 'general')} | Confidence: {conf:.2f} | Applied: {w.get('times_applied', 0)}x)")

    # Recent Chat
    if data.get('chat'):
        lines.append("\n\n## RECENT COLLABORATION (Last 7 Days)")
        lines.append("-" * 60)
        for c in reversed(data['chat'][-50:]):  # Show chronologically
            ts = c['created_at'].strftime('%m-%d %H:%M') if c.get('created_at') else ''
            lines.append(f"[{ts}] {c['participant']}: {c['content'][:200]}")

    # Memory Boxes (Topic-Continuous Groups)
    if data.get('membox'):
        boxes = data['membox'].get('boxes', [])
        links = data['membox'].get('links', [])
        if boxes:
            lines.append("\n\n## MEMORY BOXES (Topic-Continuous Groups)")
            lines.append("-" * 60)
            for b in boxes:
                lines.append(f"\n### {b['topic'][:80]}")
                score = float(b['pheromone_score']) if b.get('pheromone_score') else 0
                lines.append(f"Memories: {b.get('memory_count', 0)} | Score: {score:.1f}")
                if b.get('keywords'):
                    kw = b['keywords'] if isinstance(b['keywords'], list) else []
                    lines.append(f"Keywords: {', '.join(kw[:8])}")
                if b.get('events'):
                    ev = b['events'] if isinstance(b['events'], list) else []
                    lines.append(f"Events: {', '.join(ev[:5])}")
                if b.get('summary'):
                    lines.append(f"Summary: {b['summary'][:200]}")

            if links:
                lines.append("\n### Trace Links (Cross-Topic Connections)")
                for lk in links[:20]:
                    lines.append(f"  → {lk.get('target_topic', 'unknown')[:50]} (via: {', '.join((lk.get('linking_events') or [])[:3])})")

    lines.append("\n" + "=" * 80)
    lines.append("END MEMPHEROMONE CONTEXT")
    lines.append("=" * 80)

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Export mempheromone database for RLM')
    parser.add_argument('--output', '-o', default='/tmp/mempheromone_context.txt',
                        help='Output file path')
    parser.add_argument('--json', '-j', action='store_true',
                        help='Output as JSON instead of text')
    parser.add_argument('--memories', type=int, default=500,
                        help='Max claude_memories to export')
    parser.add_argument('--facts', type=int, default=500,
                        help='Max debugging_facts to export')
    parser.add_argument('--min-score', type=float, default=10,
                        help='Minimum pheromone score for facts')
    parser.add_argument('--quiet', '-q', action='store_true',
                        help='Suppress progress output')

    args = parser.parse_args()

    if not args.quiet:
        print("Connecting to mempheromone database...")

    conn = get_connection()

    try:
        data = {}

        if not args.quiet:
            print("Exporting claude_memories...")
        data['memories'] = export_claude_memories(conn, args.memories)

        if not args.quiet:
            print("Exporting debugging_facts...")
        data['facts'] = export_debugging_facts(conn, args.min_score, args.facts)

        if not args.quiet:
            print("Exporting session_narratives...")
        data['narratives'] = export_session_narratives(conn)

        if not args.quiet:
            print("Exporting crystallizations...")
        data['crystallizations'] = export_crystallizations(conn)

        if not args.quiet:
            print("Exporting wisdom...")
        data['wisdom'] = export_wisdom(conn)

        if not args.quiet:
            print("Exporting recent chat...")
        data['chat'] = export_recent_chat(conn)

        if not args.quiet:
            print("Exporting exocortex memories...")
        data['exocortex'] = export_exocortex_memories(conn)

        if not args.quiet:
            print("Exporting memory boxes...")
        data['membox'] = export_memory_boxes(conn)

        # Format output
        if args.json:
            # Convert datetimes to strings for JSON
            def serialize(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                return str(obj)

            output = json.dumps(data, default=serialize, indent=2)
        else:
            output = format_for_rlm(data)

        # Write to file
        with open(args.output, 'w') as f:
            f.write(output)

        # Print stats
        membox_data = data.get('membox', {})
        stats = {
            'memories': len(data['memories']),
            'facts': len(data['facts']),
            'narratives': len(data['narratives']),
            'crystallizations': len(data['crystallizations']),
            'wisdom': len(data['wisdom']),
            'chat': len(data['chat']),
            'exocortex': len(data['exocortex']),
            'membox_boxes': len(membox_data.get('boxes', [])),
            'membox_links': len(membox_data.get('links', [])),
            'output_size': len(output),
            'output_file': args.output
        }

        if not args.quiet:
            print(f"\nExport complete:")
            print(f"  Memories: {stats['memories']}")
            print(f"  Facts: {stats['facts']}")
            print(f"  Narratives: {stats['narratives']}")
            print(f"  Crystallizations: {stats['crystallizations']}")
            print(f"  Wisdom: {stats['wisdom']}")
            print(f"  Chat: {stats['chat']}")
            print(f"  Exocortex: {stats['exocortex']}")
            print(f"  Membox: {stats['membox_boxes']} boxes, {stats['membox_links']} links")
            print(f"  Output size: {stats['output_size']:,} chars")
            print(f"  Written to: {args.output}")

        # Output stats as JSON for hook parsing
        print(json.dumps(stats))

    finally:
        conn.close()


if __name__ == '__main__':
    main()
