"""
Mempheromone Membox - Topic-Continuous Memory Architecture

Adapted from MIT Membox paper for mempheromone integration.
Implements Topic Loom (sliding window topic continuation) and
Trace Weaver (cross-discontinuity event linking).

Key differences from original Membox:
- Uses local embedding model instead of OpenAI
- Integrates with existing mempheromone tables (debugging_facts, claude_memories, etc.)
- Pheromone scoring for memory box quality
- Designed for scaffolding without training

Usage:
    from mempheromone_membox import MemboxBuilder, TopicLoom, TraceWeaver

    builder = MemboxBuilder()

    # Process new memories into topic-continuous boxes
    box = builder.add_memory(memory_type='debugging_fact', memory_id=uuid, content=text)

    # Link boxes across discontinuities via shared events
    weaver = TraceWeaver()
    links = weaver.find_links(box_id)
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

import numpy as np
import psycopg2
import psycopg2.extras
from psycopg2.extras import RealDictCursor

# Import from Speakeasy infrastructure
try:
    from connection_pool import get_connection, get_connection_with_commit
except ImportError:
    # Fallback for standalone use
    import os
    from contextlib import contextmanager
    from dotenv import load_dotenv
    load_dotenv(os.path.expanduser("~/.god-mode-credentials"))

    @contextmanager
    def get_connection():
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME", "mempheromone"),
            user=os.getenv("DB_USER", "ike"),
            host=os.getenv("DB_HOST", ""),
            port=os.getenv("DB_PORT", "5432")
        )
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def get_connection_with_commit():
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME", "mempheromone"),
            user=os.getenv("DB_USER", "ike"),
            host=os.getenv("DB_HOST", ""),
            port=os.getenv("DB_PORT", "5432")
        )
        try:
            yield conn
            conn.commit()
        except:
            conn.rollback()
            raise
        finally:
            conn.close()

# Optional: sentence-transformers for semantic similarity
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
    _embedding_model = None

    def get_embedding_model():
        global _embedding_model
        if _embedding_model is None:
            _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        return _embedding_model
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    def get_embedding_model():
        return None

psycopg2.extras.register_uuid()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

# Topic continuation threshold (cosine similarity)
# Lowered from 0.6 to 0.5 for better grouping (2026-01-29)
TOPIC_CONTINUATION_THRESHOLD = 0.5

# Sliding window size for topic detection
# Increased from 5 to 10 for longer memory (2026-01-29)
TOPIC_WINDOW_SIZE = 10

# Event similarity threshold for trace linking
# Lowered from 0.7 to 0.5 for more cross-topic links (2026-01-29)
EVENT_LINK_THRESHOLD = 0.5

# Maximum events to extract per memory
MAX_EVENTS_PER_MEMORY = 5

# Keywords extraction - common tech terms to identify
TECH_KEYWORDS = {
    'python', 'javascript', 'typescript', 'rust', 'go', 'java', 'sql',
    'api', 'database', 'server', 'client', 'frontend', 'backend',
    'bug', 'error', 'fix', 'refactor', 'test', 'deploy', 'build',
    'memory', 'performance', 'security', 'authentication', 'cache',
    'async', 'sync', 'parallel', 'concurrent', 'thread', 'process',
    'git', 'commit', 'branch', 'merge', 'pull', 'push', 'rebase',
    'mcp', 'hook', 'plugin', 'extension', 'tool', 'agent', 'llm',
    'pheromone', 'crystallization', 'embedding', 'vector', 'search',
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class MemoryBox:
    """A topic-continuous group of related memories."""
    id: UUID
    topic: str
    keywords: List[str]
    events: List[str]
    summary: Optional[str] = None
    memory_count: int = 0
    pheromone_score: float = 10.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    is_active: bool = True


@dataclass
class TraceLink:
    """A connection between memory boxes via shared events."""
    id: UUID
    source_box_id: UUID
    target_box_id: UUID
    link_type: str
    similarity_score: float
    linking_events: List[str]


@dataclass
class TopicSignature:
    """Extracted topic information from content."""
    topic: str
    keywords: List[str]
    events: List[str]
    embedding: Optional[np.ndarray] = None


# =============================================================================
# TOPIC LOOM - Sliding Window Topic Continuation
# =============================================================================

class TopicLoom:
    """
    Implements sliding window topic continuation detection.

    The Topic Loom maintains a window of recent topic signatures and
    determines if new content continues an existing topic or starts
    a new one. This enables topic-continuous memory grouping.
    """

    def __init__(self, window_size: int = TOPIC_WINDOW_SIZE):
        self.window_size = window_size
        self.topic_window: List[TopicSignature] = []
        self.model = get_embedding_model() if EMBEDDINGS_AVAILABLE else None

    def extract_topic_signature(self, content: str) -> TopicSignature:
        """
        Extract topic, keywords, and events from content.

        Uses keyword-based extraction for efficiency.
        Original Membox uses LLM, but this approach is faster
        and doesn't require API calls.
        """
        content_lower = content.lower()
        words = set(re.findall(r'\b[a-z]+\b', content_lower))

        # Extract keywords (tech terms present in content)
        keywords = list(words & TECH_KEYWORDS)[:10]

        # Extract events (action patterns)
        events = self._extract_events(content)

        # Derive topic from first line or dominant keywords
        lines = content.strip().split('\n')
        topic = lines[0][:100] if lines else 'Unknown'

        # Compute embedding if available
        embedding = None
        if self.model:
            embedding = self.model.encode(content[:1000])  # Limit for speed

        return TopicSignature(
            topic=topic,
            keywords=keywords,
            events=events,
            embedding=embedding
        )

    def _extract_events(self, content: str) -> List[str]:
        """
        Extract event patterns from content.

        Events are action-oriented phrases that can link
        related memories across topic boundaries.
        """
        events = []

        # Common event patterns
        patterns = [
            r'(?:fixed|fix|resolved|resolve)\s+([^.!?\n]+)',
            r'(?:implemented|implement|added|add)\s+([^.!?\n]+)',
            r'(?:created|create|built|build)\s+([^.!?\n]+)',
            r'(?:updated|update|changed|change)\s+([^.!?\n]+)',
            r'(?:deleted|delete|removed|remove)\s+([^.!?\n]+)',
            r'(?:discovered|discover|found|find)\s+([^.!?\n]+)',
            r'(?:configured|configure|setup|set up)\s+([^.!?\n]+)',
            r'(?:debugged|debug|diagnosed|diagnose)\s+([^.!?\n]+)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches[:2]:  # Max 2 per pattern
                event = match.strip()[:80]
                if event and len(event) > 5:
                    events.append(event)

        return events[:MAX_EVENTS_PER_MEMORY]

    def is_topic_continuation(
        self,
        new_signature: TopicSignature,
        threshold: float = TOPIC_CONTINUATION_THRESHOLD
    ) -> Tuple[bool, Optional[UUID]]:
        """
        Check if new content continues an existing topic.

        Returns (is_continuation, matching_box_id if continuing)
        """
        if not self.topic_window:
            return False, None

        # Try embedding similarity first (most accurate)
        if self.model and new_signature.embedding is not None:
            best_score = 0.0
            best_box = None

            for sig in self.topic_window[-self.window_size:]:
                if sig.embedding is not None:
                    score = np.dot(new_signature.embedding, sig.embedding) / (
                        np.linalg.norm(new_signature.embedding) *
                        np.linalg.norm(sig.embedding)
                    )
                    if score > best_score:
                        best_score = score
                        best_box = getattr(sig, 'box_id', None)

            if best_score >= threshold:
                return True, best_box

        # Fallback to keyword overlap
        new_keywords = set(new_signature.keywords)
        if new_keywords:
            for sig in reversed(self.topic_window[-self.window_size:]):
                sig_keywords = set(sig.keywords)
                if sig_keywords:
                    overlap = len(new_keywords & sig_keywords) / len(new_keywords | sig_keywords)
                    if overlap >= threshold:
                        return True, getattr(sig, 'box_id', None)

        return False, None

    def add_to_window(self, signature: TopicSignature, box_id: UUID):
        """Add a topic signature to the sliding window."""
        signature.box_id = box_id
        self.topic_window.append(signature)

        # Trim window to size
        if len(self.topic_window) > self.window_size * 2:
            self.topic_window = self.topic_window[-self.window_size:]


# =============================================================================
# TRACE WEAVER - Cross-Discontinuity Event Linking
# =============================================================================

class TraceWeaver:
    """
    Implements cross-discontinuity event linking.

    The Trace Weaver connects memory boxes that share similar events,
    enabling navigation across topic boundaries. This is key for
    finding related work that may not be topically similar but
    involves similar actions.
    """

    def __init__(self, similarity_threshold: float = EVENT_LINK_THRESHOLD):
        self.similarity_threshold = similarity_threshold
        self.model = get_embedding_model() if EMBEDDINGS_AVAILABLE else None

    def find_links(
        self,
        box_id: UUID,
        max_links: int = 10
    ) -> List[TraceLink]:
        """
        Find boxes linked to the given box via shared events.
        """
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get source box events
                cur.execute("""
                    SELECT events FROM memory_boxes WHERE id = %s
                """, (box_id,))
                row = cur.fetchone()
                if not row or not row['events']:
                    return []

                source_events = set(row['events'])

                # Find boxes with overlapping events
                cur.execute("""
                    SELECT id, events, topic
                    FROM memory_boxes
                    WHERE id != %s
                      AND is_active = TRUE
                      AND events && %s  -- Array overlap operator
                    ORDER BY pheromone_score DESC
                    LIMIT %s
                """, (box_id, list(source_events), max_links * 2))

                candidates = cur.fetchall()

        links = []
        for candidate in candidates:
            target_events = set(candidate['events'])
            common_events = source_events & target_events

            if common_events:
                # Jaccard similarity
                similarity = len(common_events) / len(source_events | target_events)

                if similarity >= self.similarity_threshold or len(common_events) >= 2:
                    link = TraceLink(
                        id=uuid4(),
                        source_box_id=box_id,
                        target_box_id=candidate['id'],
                        link_type='event_similarity',
                        similarity_score=similarity,
                        linking_events=list(common_events)
                    )
                    links.append(link)

        # Sort by similarity and limit
        links.sort(key=lambda x: x.similarity_score, reverse=True)
        return links[:max_links]

    def save_links(self, links: List[TraceLink]):
        """Persist trace links to database."""
        if not links:
            return

        with get_connection_with_commit() as conn:
            with conn.cursor() as cur:
                for link in links:
                    cur.execute("""
                        INSERT INTO trace_links
                            (id, source_box_id, target_box_id, link_type,
                             similarity_score, linking_events)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (source_box_id, target_box_id) DO UPDATE
                        SET similarity_score = EXCLUDED.similarity_score,
                            linking_events = EXCLUDED.linking_events
                    """, (
                        link.id,
                        link.source_box_id,
                        link.target_box_id,
                        link.link_type,
                        link.similarity_score,
                        link.linking_events
                    ))


# =============================================================================
# MEMBOX BUILDER - Main Interface
# =============================================================================

class MemboxBuilder:
    """
    Main interface for building topic-continuous memory boxes.

    Combines Topic Loom for grouping and Trace Weaver for linking
    to create a navigable memory structure.
    """

    def __init__(
        self,
        topic_window_size: int = TOPIC_WINDOW_SIZE,
        continuation_threshold: float = TOPIC_CONTINUATION_THRESHOLD,
        link_threshold: float = EVENT_LINK_THRESHOLD
    ):
        self.loom = TopicLoom(window_size=topic_window_size)
        self.loom_threshold = continuation_threshold
        self.weaver = TraceWeaver(similarity_threshold=link_threshold)
        self.current_box_id: Optional[UUID] = None

        # Load recent boxes into topic window
        self._load_recent_boxes()

    def _load_recent_boxes(self, limit: int = 20):
        """Load recent active boxes into topic window for continuity."""
        try:
            with get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT id, topic, keywords, events
                        FROM memory_boxes
                        WHERE is_active = TRUE
                        ORDER BY updated_at DESC
                        LIMIT %s
                    """, (limit,))

                    for row in cur.fetchall():
                        sig = TopicSignature(
                            topic=row['topic'],
                            keywords=row['keywords'] or [],
                            events=row['events'] or []
                        )
                        sig.box_id = row['id']
                        self.loom.topic_window.append(sig)
        except Exception as e:
            logger.warning(f"Failed to load recent boxes: {e}")

    def add_memory(
        self,
        memory_type: str,
        memory_id: UUID,
        content: str,
        timestamp: Optional[datetime] = None
    ) -> MemoryBox:
        """
        Add a memory to the appropriate topic-continuous box.

        Args:
            memory_type: One of 'debugging_fact', 'claude_memory',
                        'crystallization', 'narrative'
            memory_id: UUID of the memory in its source table
            content: Text content of the memory
            timestamp: When the memory was created

        Returns:
            The MemoryBox the memory was added to
        """
        timestamp = timestamp or datetime.now()

        # Extract topic signature
        signature = self.loom.extract_topic_signature(content)

        # Check for topic continuation
        is_continuation, matching_box_id = self.loom.is_topic_continuation(
            signature,
            threshold=self.loom_threshold
        )

        if is_continuation and matching_box_id:
            # Add to existing box
            box = self._add_to_existing_box(
                matching_box_id, memory_type, memory_id,
                signature, timestamp
            )
        else:
            # Create new box
            box = self._create_new_box(
                memory_type, memory_id,
                signature, timestamp
            )

        # Update topic window
        self.loom.add_to_window(signature, box.id)
        self.current_box_id = box.id

        # Find and save trace links (async-friendly, could be backgrounded)
        links = self.weaver.find_links(box.id)
        if links:
            self.weaver.save_links(links)
            logger.info(f"Created {len(links)} trace links for box {box.id}")

        return box

    def _create_new_box(
        self,
        memory_type: str,
        memory_id: UUID,
        signature: TopicSignature,
        timestamp: datetime
    ) -> MemoryBox:
        """Create a new memory box."""
        box_id = uuid4()

        with get_connection_with_commit() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Create box
                cur.execute("""
                    INSERT INTO memory_boxes
                        (id, topic, keywords, events, memory_count,
                         start_time, end_time, pheromone_score)
                    VALUES (%s, %s, %s, %s, 1, %s, %s, 10.0)
                    RETURNING *
                """, (
                    box_id,
                    signature.topic,
                    signature.keywords,
                    signature.events,
                    timestamp,
                    timestamp
                ))
                row = cur.fetchone()

                # Link memory to box
                cur.execute("""
                    INSERT INTO memory_box_items
                        (box_id, memory_type, memory_id, position)
                    VALUES (%s, %s, %s, 1)
                """, (box_id, memory_type, memory_id))

        logger.info(f"Created new memory box: {signature.topic[:50]}...")

        return MemoryBox(
            id=box_id,
            topic=signature.topic,
            keywords=signature.keywords,
            events=signature.events,
            memory_count=1,
            start_time=timestamp,
            end_time=timestamp
        )

    def _add_to_existing_box(
        self,
        box_id: UUID,
        memory_type: str,
        memory_id: UUID,
        signature: TopicSignature,
        timestamp: datetime
    ) -> MemoryBox:
        """Add memory to an existing box."""
        with get_connection_with_commit() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get current box state
                cur.execute("""
                    SELECT * FROM memory_boxes WHERE id = %s
                """, (box_id,))
                box_row = cur.fetchone()

                # Merge keywords and events
                current_keywords = set(box_row['keywords'] or [])
                current_events = set(box_row['events'] or [])

                merged_keywords = list(current_keywords | set(signature.keywords))[:20]
                merged_events = list(current_events | set(signature.events))[:20]

                # Update box
                cur.execute("""
                    UPDATE memory_boxes
                    SET keywords = %s,
                        events = %s,
                        memory_count = memory_count + 1,
                        end_time = %s,
                        updated_at = NOW(),
                        pheromone_score = pheromone_score + 0.5
                    WHERE id = %s
                    RETURNING *
                """, (merged_keywords, merged_events, timestamp, box_id))
                updated_row = cur.fetchone()

                # Get next position
                cur.execute("""
                    SELECT COALESCE(MAX(position), 0) + 1 as next_pos
                    FROM memory_box_items WHERE box_id = %s
                """, (box_id,))
                next_pos = cur.fetchone()['next_pos']

                # Link memory to box
                cur.execute("""
                    INSERT INTO memory_box_items
                        (box_id, memory_type, memory_id, position)
                    VALUES (%s, %s, %s, %s)
                """, (box_id, memory_type, memory_id, next_pos))

        logger.info(f"Added memory to existing box: {box_row['topic'][:50]}...")

        return MemoryBox(
            id=box_id,
            topic=updated_row['topic'],
            keywords=merged_keywords,
            events=merged_events,
            memory_count=updated_row['memory_count'],
            pheromone_score=updated_row['pheromone_score'],
            start_time=updated_row['start_time'],
            end_time=timestamp
        )

    def get_box(self, box_id: UUID) -> Optional[MemoryBox]:
        """Get a memory box by ID."""
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM memory_boxes WHERE id = %s
                """, (box_id,))
                row = cur.fetchone()

                if row:
                    return MemoryBox(
                        id=row['id'],
                        topic=row['topic'],
                        keywords=row['keywords'] or [],
                        events=row['events'] or [],
                        summary=row['summary'],
                        memory_count=row['memory_count'],
                        pheromone_score=row['pheromone_score'],
                        start_time=row['start_time'],
                        end_time=row['end_time'],
                        is_active=row['is_active']
                    )
        return None

    def get_box_memories(self, box_id: UUID) -> List[Dict]:
        """Get all memories in a box with their content."""
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT mbi.memory_type, mbi.memory_id, mbi.position
                    FROM memory_box_items mbi
                    WHERE mbi.box_id = %s
                    ORDER BY mbi.position
                """, (box_id,))

                items = cur.fetchall()
                memories = []

                for item in items:
                    content = self._fetch_memory_content(
                        cur, item['memory_type'], item['memory_id']
                    )
                    if content:
                        memories.append({
                            'type': item['memory_type'],
                            'id': item['memory_id'],
                            'position': item['position'],
                            'content': content
                        })

                return memories

    def _fetch_memory_content(
        self,
        cursor,
        memory_type: str,
        memory_id: UUID
    ) -> Optional[str]:
        """Fetch content for a memory based on its type."""
        # Map memory types to (table, id_column, content_expression)
        tables = {
            'debugging_fact': ('debugging_facts', 'fact_id', "symptom || ': ' || solution"),
            'claude_memory': ('claude_memories', 'id', 'content'),
            'crystallization': ('crystallization_events', 'id', 'COALESCE(understanding_as_crystallized, resolving_content)'),
            'narrative': ('session_narratives', 'id', 'narrative_text'),
        }

        if memory_type not in tables:
            return None

        table, id_col, content_col = tables[memory_type]
        cursor.execute(f"""
            SELECT {content_col} as content FROM {table} WHERE {id_col} = %s
        """, (memory_id,))
        row = cursor.fetchone()
        return row['content'] if row else None

    def search_boxes(
        self,
        query: str,
        limit: int = 10,
        min_pheromone: float = 5.0
    ) -> List[MemoryBox]:
        """Search for memory boxes by topic or keywords."""
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Full-text search on topic
                cur.execute("""
                    SELECT *,
                           ts_rank(to_tsvector('english', topic),
                                   plainto_tsquery('english', %s)) as rank
                    FROM memory_boxes
                    WHERE is_active = TRUE
                      AND pheromone_score >= %s
                      AND (
                          to_tsvector('english', topic) @@ plainto_tsquery('english', %s)
                          OR %s = ANY(keywords)
                      )
                    ORDER BY rank DESC, pheromone_score DESC
                    LIMIT %s
                """, (query, min_pheromone, query, query.lower(), limit))

                return [
                    MemoryBox(
                        id=row['id'],
                        topic=row['topic'],
                        keywords=row['keywords'] or [],
                        events=row['events'] or [],
                        summary=row['summary'],
                        memory_count=row['memory_count'],
                        pheromone_score=row['pheromone_score'],
                        start_time=row['start_time'],
                        end_time=row['end_time'],
                        is_active=row['is_active']
                    )
                    for row in cur.fetchall()
                ]

    def get_linked_boxes(self, box_id: UUID) -> List[Tuple[MemoryBox, TraceLink]]:
        """Get boxes linked to this one via trace links."""
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT mb.*, tl.similarity_score, tl.linking_events, tl.link_type
                    FROM memory_boxes mb
                    JOIN trace_links tl ON mb.id = tl.target_box_id
                    WHERE tl.source_box_id = %s
                      AND mb.is_active = TRUE
                    ORDER BY tl.similarity_score DESC
                """, (box_id,))

                results = []
                for row in cur.fetchall():
                    box = MemoryBox(
                        id=row['id'],
                        topic=row['topic'],
                        keywords=row['keywords'] or [],
                        events=row['events'] or [],
                        summary=row['summary'],
                        memory_count=row['memory_count'],
                        pheromone_score=row['pheromone_score']
                    )
                    link = TraceLink(
                        id=uuid4(),
                        source_box_id=box_id,
                        target_box_id=row['id'],
                        link_type=row['link_type'],
                        similarity_score=row['similarity_score'],
                        linking_events=row['linking_events']
                    )
                    results.append((box, link))

                return results


# =============================================================================
# BATCH PROCESSING - Process existing memories into boxes
# =============================================================================

def process_existing_memories(
    memory_types: List[str] = None,
    limit: int = 1000,
    min_pheromone: float = 10.0
) -> Dict[str, int]:
    """
    Process existing memories into topic-continuous boxes.

    This bootstraps the membox system with existing mempheromone data.
    """
    memory_types = memory_types or ['debugging_fact', 'claude_memory', 'crystallization']
    builder = MemboxBuilder()
    stats = {t: 0 for t in memory_types}

    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            for memory_type in memory_types:
                # Determine table and content column
                if memory_type == 'debugging_fact':
                    query = """
                        SELECT fact_id as id, symptom || ': ' || solution as content, first_seen as created_at
                        FROM debugging_facts
                        WHERE pheromone_score >= %s
                        ORDER BY first_seen DESC
                        LIMIT %s
                    """
                    cur.execute(query, (min_pheromone, limit))
                elif memory_type == 'claude_memory':
                    query = """
                        SELECT id, content, created_at
                        FROM claude_memories
                        ORDER BY created_at DESC
                        LIMIT %s
                    """
                    cur.execute(query, (limit,))
                elif memory_type == 'crystallization':
                    query = """
                        SELECT id,
                               COALESCE(understanding_as_crystallized, resolving_content) as content,
                               created_at
                        FROM crystallization_events
                        ORDER BY created_at DESC
                        LIMIT %s
                    """
                    cur.execute(query, (limit,))
                else:
                    continue

                for row in cur.fetchall():
                    try:
                        builder.add_memory(
                            memory_type=memory_type,
                            memory_id=row['id'],
                            content=row['content'],
                            timestamp=row.get('created_at')
                        )
                        stats[memory_type] += 1
                    except Exception as e:
                        logger.warning(f"Failed to process {memory_type} {row['id']}: {e}")

    return stats


# =============================================================================
# CLI / TESTING
# =============================================================================

if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == 'bootstrap':
        # Bootstrap with existing memories
        print("Bootstrapping membox with existing memories...")
        stats = process_existing_memories(
            memory_types=['debugging_fact', 'crystallization'],
            limit=500,
            min_pheromone=12.0
        )
        print(f"Processed: {stats}")
    else:
        # Quick test
        builder = MemboxBuilder()

        # Test adding a memory
        test_box = builder.add_memory(
            memory_type='debugging_fact',
            memory_id=uuid4(),
            content="Fixed the database connection timeout by increasing pool size. The error was 'connection pool exhausted'.",
            timestamp=datetime.now()
        )

        print(f"Created box: {test_box.topic[:60]}...")
        print(f"Keywords: {test_box.keywords}")
        print(f"Events: {test_box.events}")
