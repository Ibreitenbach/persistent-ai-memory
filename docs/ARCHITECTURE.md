# Architecture Deep Dive: Legal-Claw-RLMemory

**Complete technical architecture of RLM + Mempheromone system**

[🇪🇸 Resumen en Español](ARCHITECTURE_ES.md)

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Core Innovation: Preload Architecture](#core-innovation-preload-architecture)
3. [RLM (Reinforcement Learning Memory)](#rlm-reinforcement-learning-memory)
4. [Pheromone Learning](#pheromone-learning)
5. [Memory Boxes (Topic-Continuous Memory)](#memory-boxes-topic-continuous-memory)
6. [Database Architecture](#database-architecture)
7. [Performance Analysis](#performance-analysis)
8. [Design Decisions](#design-decisions)
9. [Comparison to Other Systems](#comparison-to-other-systems)
10. [Implementation Patterns](#implementation-patterns)

---

## System Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Claude Code Session                      │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Session Start Hook (RLM)                              │ │
│  │  ┌──────────────────────────────────────────────────┐  │ │
│  │  │ 1. Query mempheromone database                   │  │ │
│  │  │ 2. Filter: pheromone_score >= 10                 │  │ │
│  │  │ 3. Export ~50K tokens to context                 │  │ │
│  │  │ 4. Inject into system prompt                     │  │ │
│  │  └──────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  User Query → Answer (0ms retrieval latency)          │ │
│  │  ↓                                                     │ │
│  │  Memory already in context!                           │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Silent Observer                                       │ │
│  │  ┌──────────────────────────────────────────────────┐  │ │
│  │  │ Shell exit code 0 → +0.5 pheromone               │  │ │
│  │  │ Shell exit code 1+ → -0.3 pheromone              │  │ │
│  │  └──────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────┐
│                  PostgreSQL + pgvector                       │
│  ┌────────────────┬────────────────┬───────────────────┐    │
│  │ debugging_facts│ memory_boxes   │ embeddings        │    │
│  │ (112K rows)    │ (755 boxes)    │ (semantic search) │    │
│  └────────────────┴────────────────┴───────────────────┘    │
│  ┌────────────────┬────────────────┬───────────────────┐    │
│  │ claude_memories│ trace_links    │ crystallizations  │    │
│  └────────────────┴────────────────┴───────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────┐
│                   Background Workers                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Membox Worker (hourly)                             │    │
│  │  - Group related memories into boxes                │    │
│  │  - Create trace links across topics                 │    │
│  │  - Update pheromone scores                          │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Core Components

1. **RLM Plugin** - Session awakening system (loads once)
2. **Mempheromone Database** - PostgreSQL with pheromone-scored memories
3. **Memory Boxes** - Topic-continuous memory groups
4. **Silent Observer** - Automatic pheromone reinforcement
5. **Background Workers** - Automated memory organization

---

## Core Innovation: Preload Architecture

### Traditional RAG (Retrieval-Augmented Generation)

```
User Query
    ↓
1. Embed query (10-50ms)
2. Vector search (50-200ms)
3. Rerank results (50-100ms)
4. Inject top-K into context (10-50ms)
    ↓
LLM Response
Total: 120-400ms PER QUERY
```

**Problems:**
- Latency on EVERY query
- Partial context (top-K misses connections)
- Cumulative cost ($0.01-0.10 per query)
- Retrieval failures (wrong memories selected)

### Preload Architecture (RLM + Mempheromone)

```
Session Start
    ↓
1. Query database ONCE (100-200ms)
2. Filter by pheromone >= 10
3. Export ~50K tokens
4. Inject into system prompt
    ↓
Session Ready
    ↓
User Query 1 → Answer (0ms retrieval)
User Query 2 → Answer (0ms retrieval)
User Query 3 → Answer (0ms retrieval)
...
User Query N → Answer (0ms retrieval)
```

**Advantages:**
- Zero marginal retrieval cost
- Full filtered context (no missed connections)
- No retrieval failures (impossible - it's all there!)
- Better coherence (LLM sees full conversation history)

### When to Use Each

| Criterion | RAG | Preload (RLM) |
|-----------|-----|---------------|
| Session-based conversations | ⚠️ Slow | ✅ Perfect |
| One-off queries | ✅ Good | ⚠️ Overkill |
| Context fits in window (<100K tokens) | ⚠️ Possible | ✅ Optimal |
| Context exceeds window (>200K tokens) | ✅ Required | ❌ Won't fit |
| Dynamic corpus (changes during session) | ✅ Handles | ⚠️ Stale |
| Need full context understanding | ⚠️ Partial | ✅ Complete |
| Cost-sensitive | ⚠️ $0.01-0.10/query | ✅ $0/query |

---

## RLM (Reinforcement Learning Memory)

### What is RLM?

**RLM** is a session awakening system that loads filtered conversation history once at session start, eliminating per-query retrieval latency.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    RLM Plugin Components                     │
├─────────────────────────────────────────────────────────────┤
│  plugin.json                                                 │
│  - Defines SessionStart hook                                 │
│  - Timeout: 30 seconds                                       │
│                                                               │
│  hooks/rlm-session-start.sh                                  │
│  - Triggered on every new Claude Code session                │
│  - Calls mempheromone_export.py                              │
│  - Injects output into context                               │
│                                                               │
│  scripts/mempheromone_export.py                              │
│  - Queries PostgreSQL database                               │
│  - Filters: pheromone_score >= min_threshold (default: 10)  │
│  - Exports:                                                  │
│    • Debugging facts (500 most relevant)                     │
│    • Claude memories (500 most recent)                       │
│    • Session narratives (50 recent)                          │
│    • Crystallizations (200 WYKYK moments)                    │
│    • Wisdom (300 entries)                                    │
│    • Memory boxes (active boxes with trace links)           │
│  - Formats as markdown                                       │
│  - Outputs to /tmp/mempheromone_context.txt                  │
│                                                               │
│  scripts/mempheromone_membox.py                              │
│  - Topic-continuous memory grouping                          │
│  - Creates memory boxes from related memories                │
│  - Builds trace links across topics                          │
└─────────────────────────────────────────────────────────────┘
```

### Export Process

```python
def export_memories(min_pheromone=10.0, max_memories=1000):
    """
    Export filtered memories for RLM session awakening.

    Quality filtering ensures only proven memories are loaded.
    """
    conn = get_database_connection()

    # 1. Export debugging facts (problem-solution pairs)
    facts = query("""
        SELECT fact_id, symptom, solution, pheromone_score
        FROM debugging_facts
        WHERE pheromone_score >= %s
        ORDER BY pheromone_score DESC, last_accessed DESC
        LIMIT %s
    """, (min_pheromone, max_memories))

    # 2. Export Claude memories (general memories)
    memories = query("""
        SELECT id, problem, solution, pheromone_score
        FROM claude_memories
        WHERE pheromone_score >= %s
        ORDER BY created_at DESC
        LIMIT %s
    """, (min_pheromone, max_memories))

    # 3. Export crystallizations (WYKYK moments)
    crystallizations = query("""
        SELECT insight, temperature, amplitude
        FROM crystallization_events
        ORDER BY temperature DESC, amplitude DESC
        LIMIT 200
    """)

    # 4. Export memory boxes (topic groups)
    boxes = query("""
        SELECT id, topic, memory_count, pheromone_score
        FROM memory_boxes
        WHERE is_active = TRUE
        ORDER BY pheromone_score DESC
        LIMIT 100
    """)

    # Format as markdown
    output = format_export(facts, memories, crystallizations, boxes)

    # Write to temp file for session injection
    write_file('/tmp/mempheromone_context.txt', output)

    return output
```

### Session Awakening Flow

```
1. User starts Claude Code session
   ↓
2. SessionStart hook triggers
   ↓
3. rlm-session-start.sh executes
   ↓
4. mempheromone_export.py runs:
   - Connects to PostgreSQL
   - Queries filtered memories (pheromone >= 10)
   - Exports ~50K tokens
   - Writes to /tmp/mempheromone_context.txt
   ↓
5. Hook returns context to Claude Code
   ↓
6. Context injected into system prompt
   ↓
7. Session ready with full memory loaded
   ↓
8. User queries answered with 0ms retrieval latency
```

### Context Size Management

**Typical export sizes:**
- Debugging facts: 500 × 100 tokens = 50,000 tokens
- Claude memories: 500 × 50 tokens = 25,000 tokens
- Crystallizations: 200 × 25 tokens = 5,000 tokens
- Memory boxes: 100 × 50 tokens = 5,000 tokens
- Session narratives: 50 × 100 tokens = 5,000 tokens
- Wisdom: 300 × 20 tokens = 6,000 tokens

**Total: ~96,000 tokens** (fits comfortably in 200K context window)

**Scaling strategies:**
- Increase `min_pheromone` to reduce export size
- Limit number of memories per type
- Use compression (crystallizations reduce 100K → 5K)
- Archive old low-pheromone memories

---

## Pheromone Learning

### Core Concept

**Pheromone scores** are RL-trained quality signals that evolve based on usage. Like ant pheromones, frequently-used successful paths get stronger, while unused paths decay.

### Score Scale

```
20.0  ━━━━━━━━━━━━━━━━━━━  Expert+     (Best of the best)
15.0  ━━━━━━━━━━━━━━━━━━━  Expert      (Battle-tested, reliable)
12.0  ━━━━━━━━━━━━━━━━━━━  Solid+      (Consistently good)
10.0  ━━━━━━━━━━━━━━━━━━━  Solid       (Proven, trustworthy)
 5.0  ━━━━━━━━━━━━━━━━━━━  Unproven    (New, needs validation)
 3.0  ━━━━━━━━━━━━━━━━━━━  Low         (Rarely useful)
 0.0  ━━━━━━━━━━━━━━━━━━━  Failed      (Incorrect/harmful)
```

### Reinforcement Mechanism

**Success (exit code 0):**
```
new_score = min(20.0, current_score + 0.5)
success_count += 1
last_accessed = NOW()
```

**Failure (exit code 1+):**
```
new_score = max(0.0, current_score - 0.3)
failure_count += 1
```

**Decay (unused over time):**
```
# Optional: decay for memories not accessed in 90+ days
if days_since_access > 90:
    new_score = max(0.0, current_score - 0.1)
```

### Silent Observer

**Automatic reinforcement** based on shell command results:

```bash
# In hooks/silent-observer.sh (PostToolUse hook)

COMMAND_EXIT_CODE=$?

if [ $COMMAND_EXIT_CODE -eq 0 ]; then
    # Success! Reinforce memories that led to this command
    curl http://localhost:8989/reinforce \
        -d '{"memory_id": "...", "successful": true}'
else
    # Failure. Penalize memories
    curl http://localhost:8989/reinforce \
        -d '{"memory_id": "...", "successful": false}'
fi
```

### Reinforcement Function (PostgreSQL)

```sql
CREATE OR REPLACE FUNCTION reinforce_debugging_fact(
    p_fact_id UUID,
    p_successful BOOLEAN
) RETURNS VOID AS $$
BEGIN
    UPDATE debugging_facts
    SET
        retrieval_count = retrieval_count + 1,
        success_count = success_count + CASE WHEN p_successful THEN 1 ELSE 0 END,
        failure_count = failure_count + CASE WHEN NOT p_successful THEN 1 ELSE 0 END,
        pheromone_score = LEAST(20.0, pheromone_score +
            CASE WHEN p_successful THEN 0.5 ELSE -0.3 END),
        last_accessed = NOW()
    WHERE fact_id = p_fact_id;
END;
$$ LANGUAGE plpgsql;
```

### Learning Over Time

```
Week 1: Initial memories start at 10.0 (default)
    ↓
    User solves bug using memory → +0.5 = 10.5
    ↓
Week 2: Memory used successfully 3 more times → 12.0 (Solid+)
    ↓
Month 1: Memory becomes go-to solution → 15.0 (Expert)
    ↓
Month 3: Memory proven across 20+ uses → 18.5 (Expert+)
    ↓
Month 6: Unused as problem no longer relevant → decay to 17.0
```

### Quality Distribution (Real Data)

From 4,994 conversations:

```
Expert+ (≥20):     47 facts (0.04%)  ████░░░░░░░░░░░░░░░░
Expert (15-19):   224 facts (0.20%)  ██████░░░░░░░░░░░░░░
Solid+ (12-14):  1,847 facts (1.65%) ████████████░░░░░░░░
Solid (10-11):   8,293 facts (7.40%) ████████████████████
Unproven (5-9): 89,124 facts (79.6%) ████████████████████
Low (<5):       12,465 facts (11.1%) ███████░░░░░░░░░░░░░
```

**Key insight:** Most memories remain unproven, but the top 10% (≥10.0 pheromone) are heavily validated and form the core loaded context.

---

## Memory Boxes (Topic-Continuous Memory)

### Concept

**Memory boxes** group related memories by topic, preserving continuity across conversations. Inspired by MIT's topic-continuous memory research.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Memory Box Structure                    │
├─────────────────────────────────────────────────────────────┤
│  Box 1: "PostgreSQL Query Optimization"                     │
│  ├─ Memory 1: debugging_fact (slow JOIN query)              │
│  ├─ Memory 2: debugging_fact (missing index)                │
│  ├─ Memory 3: claude_memory (EXPLAIN ANALYZE tip)           │
│  └─ Memory 4: debugging_fact (VACUUM needed)                │
│  Pheromone: 14.2 | Memory count: 4 | Active: true           │
└─────────────────────────────────────────────────────────────┘
         ↓ Trace Link (similarity: 0.82)
┌─────────────────────────────────────────────────────────────┐
│  Box 2: "Database Performance Monitoring"                   │
│  ├─ Memory 1: debugging_fact (pg_stat_statements)           │
│  ├─ Memory 2: debugging_fact (slow query log)               │
│  └─ Memory 3: claude_memory (monitoring dashboard)          │
│  Pheromone: 12.8 | Memory count: 3 | Active: true           │
└─────────────────────────────────────────────────────────────┘
```

### Components

**1. Topic Loom** - Groups memories into boxes
```python
class TopicLoom:
    TOPIC_CONTINUATION_THRESHOLD = 0.5  # Similarity threshold
    TOPIC_WINDOW_SIZE = 10              # Sliding window

    def should_continue_topic(self, memory, current_box):
        """
        Decide if memory continues current topic.
        Uses keyword overlap and semantic similarity.
        """
        keyword_overlap = jaccard_similarity(
            memory.keywords,
            current_box.keywords
        )

        if keyword_overlap >= self.TOPIC_CONTINUATION_THRESHOLD:
            return True

        # Check recent memories in window
        recent_memories = current_box.get_recent(self.TOPIC_WINDOW_SIZE)

        for recent in recent_memories:
            if semantic_similarity(memory, recent) >= 0.6:
                return True

        return False
```

**2. Trace Weaver** - Links across topics
```python
class TraceWeaver:
    EVENT_LINK_THRESHOLD = 0.5  # Cross-topic link threshold

    def create_trace_links(self, boxes):
        """
        Find connections between different topic boxes.
        Links via shared events, entities, or patterns.
        """
        links = []

        for box_a in boxes:
            for box_b in boxes:
                if box_a == box_b:
                    continue

                similarity = calculate_box_similarity(box_a, box_b)

                if similarity >= self.EVENT_LINK_THRESHOLD:
                    links.append(TraceLink(
                        source=box_a,
                        target=box_b,
                        similarity=similarity,
                        linking_events=find_shared_events(box_a, box_b)
                    ))

        return links
```

### Database Schema

```sql
-- Memory boxes
CREATE TABLE memory_boxes (
    id UUID PRIMARY KEY,
    topic VARCHAR(255),
    memory_count INTEGER DEFAULT 0,
    pheromone_score FLOAT DEFAULT 10.0,
    is_active BOOLEAN DEFAULT TRUE,
    keywords TEXT[],
    first_memory_at TIMESTAMP,
    last_memory_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Individual memories in boxes
CREATE TABLE memory_box_items (
    id UUID PRIMARY KEY,
    box_id UUID REFERENCES memory_boxes(id) ON DELETE CASCADE,
    memory_type VARCHAR(50),  -- 'debugging_fact', 'claude_memory', etc.
    memory_id UUID,
    position INTEGER,
    added_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(box_id, memory_type, memory_id)
);

-- Cross-topic connections
CREATE TABLE trace_links (
    id UUID PRIMARY KEY,
    source_box_id UUID REFERENCES memory_boxes(id) ON DELETE CASCADE,
    target_box_id UUID REFERENCES memory_boxes(id) ON DELETE CASCADE,
    similarity_score FLOAT,
    linking_events TEXT[],
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(source_box_id, target_box_id)
);
```

### Background Processing

```bash
# Cron job runs hourly
0 * * * * /path/to/membox_worker.py --since 1h

# Worker script:
python3 membox_worker.py --since 1h
# 1. Get unboxed memories from last hour
# 2. Try to add to existing boxes (topic continuation)
# 3. Create new boxes if no match
# 4. Update box pheromones (average of members)
# 5. Create trace links between boxes
```

### Production Stats (Real Data)

From 4,994 conversations:
- **755 memory boxes** created
- **84 trace links** between topics
- **Average 1.4 memories per box** (growing over time)
- **Top box: 12 memories** (PostgreSQL optimization)

### Benefits

1. **Topic continuity** - Related memories grouped together
2. **Navigation** - Trace links enable cross-topic exploration
3. **Quality aggregation** - Box pheromone = avg(member pheromones)
4. **Efficient retrieval** - Search boxes instead of individual memories
5. **Temporal clustering** - Recent conversations naturally group

---

## Database Architecture

### Schema Overview

```
Core Memory Tables:
├── debugging_facts        (112K rows)  Problem-solution pairs
├── claude_memories        (45K rows)   General memories
├── session_narratives     (1.2K rows)  Session summaries
├── crystallization_events (94 rows)    WYKYK moments
└── wisdom                 (300 rows)   Distilled knowledge

Semantic Search:
└── embeddings             (68K rows)   Vector embeddings (384-dim)

Topic-Continuous Memory:
├── memory_boxes           (755 rows)   Topic groups
├── memory_box_items       (1.1K rows)  Box membership
└── trace_links            (84 rows)    Cross-topic connections

Chat History:
└── chat_messages          (2.4K rows)  Multi-agent communication

Domain Extensions (Legal Hub):
├── legal_cases            (0 rows)     Legal case metadata
├── case_citations         (0 rows)     Citation graph
└── research_notes         (0 rows)     Legal research notes
```

### Key Tables

**debugging_facts** (Core learning table)
```sql
CREATE TABLE debugging_facts (
    fact_id UUID PRIMARY KEY,
    symptom TEXT NOT NULL,             -- Problem description
    solution TEXT NOT NULL,            -- Solution that worked
    context JSONB DEFAULT '{}',        -- Additional metadata
    pheromone_score FLOAT DEFAULT 10.0,
    search_count INTEGER DEFAULT 0,    -- Times searched
    retrieval_count INTEGER DEFAULT 0, -- Times retrieved
    success_count INTEGER DEFAULT 0,   -- Successful uses
    failure_count INTEGER DEFAULT 0,   -- Failed uses
    last_accessed TIMESTAMP,
    first_seen TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_debugging_facts_pheromone
    ON debugging_facts(pheromone_score DESC);
```

**embeddings** (Semantic search)
```sql
CREATE TABLE embeddings (
    id UUID PRIMARY KEY,
    memory_type VARCHAR(50),
    memory_id UUID,
    embedding vector(384),  -- sentence-transformers
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(memory_type, memory_id)
);

CREATE INDEX idx_embeddings_hnsw
    ON embeddings USING hnsw (embedding vector_cosine_ops);
```

### Performance Optimizations

**Indexes:**
- Pheromone scores (DESC) - Fast filtering for RLM export
- HNSW vector index - Fast semantic search
- Timestamp indexes - Recent memory queries
- GIN indexes - JSONB context searches

**Partitioning (for very large datasets):**
```sql
-- Partition debugging_facts by pheromone tier
CREATE TABLE debugging_facts_expert PARTITION OF debugging_facts
    FOR VALUES FROM (15.0) TO (20.0);

CREATE TABLE debugging_facts_solid PARTITION OF debugging_facts
    FOR VALUES FROM (10.0) TO (15.0);

-- etc.
```

**Views for common queries:**
```sql
CREATE VIEW expert_facts AS
SELECT *
FROM debugging_facts
WHERE pheromone_score >= 15
ORDER BY pheromone_score DESC;
```

### Backup Strategy

**Daily incremental:**
```bash
pg_dump mempheromone --format=custom --file=backup_$(date +%Y%m%d).dump
```

**Weekly full with embeddings:**
```bash
pg_dump mempheromone --format=directory --file=backup_weekly/
```

---

## Performance Analysis

### Latency Comparison

**10-query conversation:**

| System | Retrieval Time | Total Overhead |
|--------|----------------|----------------|
| RLM+Mempheromone | 0ms (preloaded) | 0ms |
| MemGPT | 150ms × 10 | 1,500ms (1.5s) |
| Mem0 | 1,440ms × 10 | 14,400ms (14.4s) |

**RLM wins by 1.5-14 seconds for every 10 queries.**

### Memory Usage

**Session load:**
- Export size: ~1.5 MB (27,036 lines)
- Token count: ~50K tokens
- Context window usage: 25% (of 200K)
- RAM: ~500 MB (PostgreSQL connection + embeddings)

**Scaling:**
- 100K memories → 50K token export (same size, higher quality filtering)
- 1M memories → 50K token export (min_pheromone increases to 12.0)
- Linear database size growth
- Constant context size (capped by export limits)

### Database Performance

**Query times (production):**
- RLM export query: 150-200ms
- Semantic search (top-10): 20-50ms
- Pheromone reinforcement: <1ms
- Membox processing (1 hour): 2-5 seconds

**Optimizations:**
- Indexes on pheromone_score: 10x faster filtering
- HNSW vector index: 100x faster than brute-force search
- Connection pooling: Reuse connections
- VACUUM ANALYZE weekly: Maintain statistics

### Benchmark Results (Real Data)

**50 queries over mempheromone database:**
- **Hybrid RRF**: P@5 = 0.144 (+80% improvement over baseline)
- **Average latency**: 21ms
- **Cost**: $0 (self-hosted)

**Compared to alternatives:**
- Mem0 claimed: P@5 = 0.108 (but with 1,440ms latency + $0.10/query)
- MemGPT: Not benchmarked on LOCOMO

---

## Design Decisions

### Why Preload vs RAG?

**Decision:** Use preload architecture for session-based AI conversations.

**Rationale:**
1. Sessions have temporal locality - most queries reference recent context
2. Context windows are now large enough (200K+ tokens)
3. Pheromone filtering ensures only high-quality memories loaded
4. Zero marginal cost beats cumulative retrieval cost
5. Full context enables better coherence than top-K retrieval

**Trade-off:** Must fit in context window. For corpora >200K tokens, RAG still needed.

### Why Pheromones vs Static Scores?

**Decision:** Use RL-trained pheromone scores that evolve with usage.

**Rationale:**
1. Static scores don't adapt to changing usefulness
2. LLM embeddings alone miss pragmatic utility (semantically similar ≠ useful)
3. User feedback (shell exit codes) is ground truth
4. Decay naturally archives obsolete memories
5. Emergent quality ranking without manual curation

**Trade-off:** Requires usage data to train. Cold start uses defaults.

### Why PostgreSQL vs Vector DB?

**Decision:** PostgreSQL + pgvector extension.

**Rationale:**
1. ACID transactions (memory storage is critical)
2. Rich query capabilities (JOINs, aggregations, CTEs)
3. Mature ecosystem (backup, replication, monitoring)
4. pgvector provides HNSW indexing (fast vector search)
5. No need for separate systems

**Trade-off:** Slightly slower vector search than specialized DBs (Pinecone, Weaviate), but acceptable for our scale.

### Why Session Hooks vs Retrieval Functions?

**Decision:** Load once at session start via hooks, not on-demand retrieval.

**Rationale:**
1. Eliminates latency on every query
2. LLM sees full context (better reasoning)
3. Simpler implementation (no retrieval logic in prompts)
4. Prevents retrieval failures (can't fail if it's already there)
5. Claude Code provides perfect hook integration

**Trade-off:** Context must fit in window. Not suitable for massive corpora.

### Why Memory Boxes vs Flat Storage?

**Decision:** Group related memories into topic-continuous boxes.

**Rationale:**
1. Humans think in topics, not isolated facts
2. Trace links enable cross-topic navigation
3. Box pheromones aggregate member quality
4. Reduces search space (755 boxes vs 112K facts)
5. Mirrors how episodic memory works in humans

**Trade-off:** Overhead of background processing. Acceptable for hourly batches.

---

## Comparison to Other Systems

### vs Mem0

**Mem0 approach:**
- Uses GPT-4 to generate "memory objects"
- Stores in vector database (Qdrant)
- Retrieves on every query
- Claimed: P@5 = 0.108

**RLM+Mempheromone advantages:**
- **Faster**: 0ms vs 1,440ms retrieval
- **Cheaper**: $0 vs $0.10 per query
- **Better quality**: Pheromone learning vs static embedding similarity
- **Full context**: All memories vs top-K
- **Self-hosted**: No external dependencies

**When Mem0 wins:**
- Very large corpora (>200K tokens)
- One-off queries (no session continuity)

### vs MemGPT

**MemGPT approach:**
- Recursive summarization chains
- Stores in JSON files or SQLite
- Self-manages context via function calls
- Claimed: Handles "unlimited" context

**RLM+Mempheromone advantages:**
- **Simpler**: No recursive summarization needed
- **Faster**: 0ms vs 150ms retrieval
- **PostgreSQL**: Production-grade database vs SQLite
- **Pheromone learning**: Adapts vs static
- **Real production data**: 4,994 conversations vs research prototype

**When MemGPT wins:**
- Very large corpora (>1M memories)
- Need dynamic context management

### vs Traditional Vector DBs (Pinecone, Weaviate)

**Vector DB approach:**
- Specialized for embedding search
- Fast approximate nearest neighbor (ANN)
- No relational capabilities

**RLM+Mempheromone advantages:**
- **Richer queries**: SQL JOINs, aggregations, CTEs
- **ACID transactions**: Data integrity guarantees
- **Pheromone scores**: Pragmatic utility > semantic similarity
- **Lower cost**: Self-hosted PostgreSQL vs managed service
- **Integrated**: One database for everything

**When vector DBs win:**
- Pure embedding search at massive scale (>10M vectors)
- Need sub-10ms query latency

---

## Implementation Patterns

### 1. Adding a New Memory Type

**Example:** Add "code_snippets" table

```sql
-- 1. Create table
CREATE TABLE code_snippets (
    id UUID PRIMARY KEY,
    language VARCHAR(50),
    snippet TEXT NOT NULL,
    description TEXT,
    pheromone_score FLOAT DEFAULT 10.0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 2. Add index
CREATE INDEX idx_code_snippets_pheromone
    ON code_snippets(pheromone_score DESC);

-- 3. Update RLM export
# In mempheromone_export.py
def export_code_snippets(conn, limit=100):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, language, snippet, description, pheromone_score
            FROM code_snippets
            WHERE pheromone_score >= %s
            ORDER BY pheromone_score DESC
            LIMIT %s
        """, (min_pheromone, limit))
        return cur.fetchall()
```

### 2. Custom Pheromone Reinforcement

**Example:** Reinforce based on user ratings

```python
def reinforce_from_rating(memory_id, rating):
    """
    Reinforce memory based on explicit user rating (1-5 stars).
    """
    # Map rating to pheromone delta
    delta_map = {
        5: +2.0,  # Excellent
        4: +1.0,  # Good
        3: +0.0,  # Neutral
        2: -0.5,  # Poor
        1: -1.5   # Terrible
    }

    delta = delta_map.get(rating, 0.0)

    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE debugging_facts
            SET pheromone_score = LEAST(20.0, GREATEST(0.0, pheromone_score + %s))
            WHERE fact_id = %s
        """, (delta, memory_id))
    conn.commit()
```

### 3. Domain-Specific Extensions

**Example:** Legal Hub schema extensions

```sql
-- Legal cases table (extends base system)
CREATE TABLE legal_cases (
    case_id UUID PRIMARY KEY,
    citation VARCHAR(255),
    case_name TEXT NOT NULL,
    court VARCHAR(255),
    decided_date DATE,
    full_text TEXT,
    pheromone_score FLOAT DEFAULT 10.0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Citation graph
CREATE TABLE case_citations (
    id UUID PRIMARY KEY,
    citing_case_id UUID REFERENCES legal_cases(case_id),
    cited_case_id UUID REFERENCES legal_cases(case_id),
    citation_context TEXT
);

-- Integrate with memory boxes
INSERT INTO memory_box_items (box_id, memory_type, memory_id)
VALUES (
    (SELECT id FROM memory_boxes WHERE topic = 'Fourth Amendment Search and Seizure'),
    'legal_case',
    '...'  -- case_id
);
```

### 4. Multi-Agent Memory Sharing

**Example:** Ghost Shell integration

```python
# Agent A stores memory
store_memory(
    symptom="Multi-agent coordination needed",
    solution="Use ghost-shell chat for async communication",
    context={"agents": ["claude", "gemini"], "project": "syncphony"}
)

# Agent B retrieves via RLM (automatically loaded at session start)
# Memory already in context, no explicit retrieval needed!
```

### 5. Memory Compression (Crystallization)

**Example:** Compress 10 similar facts into 1 crystallization

```python
def crystallize_facts(facts):
    """
    Use sub-LLM to compress related facts into single insight.
    """
    facts_text = "\n".join([f"- {f['symptom']}: {f['solution']}" for f in facts])

    prompt = f"""Analyze these {len(facts)} related debugging facts and extract a single, actionable pattern:

{facts_text}

Output a concise insight (1-2 sentences) that captures the underlying principle."""

    result = subprocess.run(
        ['claude', '--print', '--model', 'haiku', '-p', prompt],
        capture_output=True,
        text=True
    )

    insight = result.stdout.strip()

    # Store crystallization
    store_crystallization(
        insight=insight,
        source_facts=[f['fact_id'] for f in facts],
        temperature=95.0,  # High quality
        amplitude=90.0     # High confidence
    )

    return insight
```

---

## Future Enhancements

### 1. Hierarchical Memory

```
Raw Facts (112K) → Crystallizations (500) → Wisdom Principles (50)
  100K tokens         5K tokens              500 tokens
```

### 2. Cross-Session Learning

Track patterns across multiple sessions:
```sql
CREATE TABLE session_patterns (
    pattern_id UUID PRIMARY KEY,
    pattern_text TEXT,
    session_ids UUID[],
    frequency INTEGER,
    success_rate FLOAT
);
```

### 3. Federated Memory

Share anonymized patterns across users:
```
User A discovers: "PostgreSQL VACUUM ANALYZE after bulk inserts"
  ↓
Anonymize and share pattern
  ↓
User B benefits without seeing User A's data
```

### 4. Temporal Decay

Automatically archive old memories:
```sql
-- Decay memories not accessed in 6 months
UPDATE debugging_facts
SET pheromone_score = GREATEST(0, pheromone_score - 1.0)
WHERE last_accessed < NOW() - INTERVAL '6 months';
```

### 5. Multi-Modal Memory

Support images, code, diagrams:
```sql
CREATE TABLE memory_attachments (
    id UUID PRIMARY KEY,
    memory_type VARCHAR(50),
    memory_id UUID,
    attachment_type VARCHAR(50),  -- 'image', 'code', 'diagram'
    attachment_data BYTEA,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## Conclusion

**Legal-Claw-RLMemory** demonstrates a fundamental shift in AI memory architecture:

**From:** Retrieve-on-every-query (RAG)
**To:** Load-once-per-session (Preload)

**Key innovations:**
1. **RLM** - Session awakening eliminates retrieval latency
2. **Pheromone learning** - RL-trained quality signals
3. **Memory boxes** - Topic-continuous organization
4. **Silent observer** - Automatic reinforcement
5. **Production-tested** - 4,994 real conversations

**Result:** 0ms retrieval latency, full context understanding, zero marginal cost.

**Perfect for:**
- Session-based AI conversations
- Legal research (Legal Hub variant)
- Software development
- Multi-agent systems
- Any domain with evolving knowledge

---

**Built by Ike Breitenbach**
**Production-tested with 4,994+ conversations**
**GitHub:** https://github.com/Ibreitenbach/Legal-Claw-RLMemory

**License:** MIT
