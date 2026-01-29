-- Persistent AI Memory: Complete Database Schema
-- Mempheromone + RLM System

-- Enable pgvector extension (optional, for semantic search)
CREATE EXTENSION IF NOT EXISTS vector;

-- =============================================================================
-- Core Memory Tables
-- =============================================================================

-- Debugging Facts: Problem-solution pairs learned from debugging
CREATE TABLE IF NOT EXISTS debugging_facts (
    fact_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symptom TEXT NOT NULL,
    solution TEXT NOT NULL,
    context JSONB DEFAULT '{}'::jsonb,
    pheromone_score FLOAT DEFAULT 10.0,
    search_count INTEGER DEFAULT 0,
    retrieval_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMP DEFAULT NOW(),
    first_seen TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Claude Memories: General memories stored by Claude
CREATE TABLE IF NOT EXISTS claude_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    problem TEXT NOT NULL,
    solution TEXT NOT NULL,
    context JSONB DEFAULT '{}'::jsonb,
    pheromone_score FLOAT DEFAULT 10.0,
    search_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Session Narratives: High-level summaries of sessions
CREATE TABLE IF NOT EXISTS session_narratives (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    narrative TEXT NOT NULL,
    session_id VARCHAR(255),
    mood VARCHAR(50),
    arc VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Crystallization Events: WYKYK moments and insights
CREATE TABLE IF NOT EXISTS crystallization_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    insight TEXT NOT NULL,
    temperature FLOAT DEFAULT 0.0,
    amplitude FLOAT DEFAULT 0.0,
    context JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Wisdom: Long-term distilled knowledge
CREATE TABLE IF NOT EXISTS wisdom (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wisdom TEXT NOT NULL,
    category VARCHAR(100),
    pheromone_score FLOAT DEFAULT 10.0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- =============================================================================
-- Embeddings (for semantic search)
-- =============================================================================

CREATE TABLE IF NOT EXISTS embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    memory_type VARCHAR(50) NOT NULL,
    memory_id UUID NOT NULL,
    embedding vector(384),  -- sentence-transformers default dimension
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(memory_type, memory_id)
);

-- =============================================================================
-- Memory Boxes (Topic-Continuous Memory)
-- =============================================================================

-- Memory Boxes: Groups of related memories
CREATE TABLE IF NOT EXISTS memory_boxes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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

-- Memory Box Items: Individual memories in boxes
CREATE TABLE IF NOT EXISTS memory_box_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    box_id UUID REFERENCES memory_boxes(id) ON DELETE CASCADE,
    memory_type VARCHAR(50) NOT NULL,
    memory_id UUID NOT NULL,
    position INTEGER,
    added_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(box_id, memory_type, memory_id)
);

-- Trace Links: Cross-topic connections
CREATE TABLE IF NOT EXISTS trace_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_box_id UUID REFERENCES memory_boxes(id) ON DELETE CASCADE,
    target_box_id UUID REFERENCES memory_boxes(id) ON DELETE CASCADE,
    similarity_score FLOAT,
    linking_events TEXT[],
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(source_box_id, target_box_id)
);

-- =============================================================================
-- Chat History (for multi-agent systems)
-- =============================================================================

CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- =============================================================================
-- Indexes for Performance
-- =============================================================================

-- Debugging facts indexes
CREATE INDEX IF NOT EXISTS idx_debugging_facts_pheromone
    ON debugging_facts(pheromone_score DESC);
CREATE INDEX IF NOT EXISTS idx_debugging_facts_accessed
    ON debugging_facts(last_accessed DESC);
CREATE INDEX IF NOT EXISTS idx_debugging_facts_created
    ON debugging_facts(created_at DESC);

-- Claude memories indexes
CREATE INDEX IF NOT EXISTS idx_claude_memories_pheromone
    ON claude_memories(pheromone_score DESC);
CREATE INDEX IF NOT EXISTS idx_claude_memories_created
    ON claude_memories(created_at DESC);

-- Memory boxes indexes
CREATE INDEX IF NOT EXISTS idx_memory_boxes_pheromone
    ON memory_boxes(pheromone_score DESC);
CREATE INDEX IF NOT EXISTS idx_memory_boxes_active
    ON memory_boxes(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_memory_boxes_updated
    ON memory_boxes(updated_at DESC);

-- Memory box items indexes
CREATE INDEX IF NOT EXISTS idx_memory_box_items_box
    ON memory_box_items(box_id);
CREATE INDEX IF NOT EXISTS idx_memory_box_items_memory
    ON memory_box_items(memory_type, memory_id);

-- Trace links indexes
CREATE INDEX IF NOT EXISTS idx_trace_links_source
    ON trace_links(source_box_id);
CREATE INDEX IF NOT EXISTS idx_trace_links_target
    ON trace_links(target_box_id);
CREATE INDEX IF NOT EXISTS idx_trace_links_similarity
    ON trace_links(similarity_score DESC);

-- Embeddings indexes (HNSW for fast vector search)
CREATE INDEX IF NOT EXISTS idx_embeddings_hnsw
    ON embeddings USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_embeddings_memory
    ON embeddings(memory_type, memory_id);

-- Session narratives indexes
CREATE INDEX IF NOT EXISTS idx_session_narratives_created
    ON session_narratives(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_session_narratives_session
    ON session_narratives(session_id);

-- Crystallizations indexes
CREATE INDEX IF NOT EXISTS idx_crystallization_events_created
    ON crystallization_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_crystallization_events_temperature
    ON crystallization_events(temperature DESC);

-- Wisdom indexes
CREATE INDEX IF NOT EXISTS idx_wisdom_pheromone
    ON wisdom(pheromone_score DESC);
CREATE INDEX IF NOT EXISTS idx_wisdom_category
    ON wisdom(category);

-- Chat messages indexes
CREATE INDEX IF NOT EXISTS idx_chat_messages_created
    ON chat_messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_messages_participant
    ON chat_messages(participant);

-- =============================================================================
-- Functions for Pheromone Reinforcement
-- =============================================================================

-- Reinforce debugging fact (increase pheromone on success)
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
        pheromone_score = LEAST(20.0, pheromone_score + CASE WHEN p_successful THEN 0.5 ELSE -0.3 END),
        last_accessed = NOW(),
        updated_at = NOW()
    WHERE fact_id = p_fact_id;
END;
$$ LANGUAGE plpgsql;

-- Reinforce memory box (update pheromone based on usage)
CREATE OR REPLACE FUNCTION reinforce_memory_box(
    p_box_id UUID,
    p_delta FLOAT
) RETURNS VOID AS $$
BEGIN
    UPDATE memory_boxes
    SET
        pheromone_score = LEAST(20.0, GREATEST(0.0, pheromone_score + p_delta)),
        updated_at = NOW()
    WHERE id = p_box_id;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Views for Common Queries
-- =============================================================================

-- Expert facts (high-quality, proven memories)
CREATE OR REPLACE VIEW expert_facts AS
SELECT *
FROM debugging_facts
WHERE pheromone_score >= 15
ORDER BY pheromone_score DESC;

-- Active memory boxes with statistics
CREATE OR REPLACE VIEW active_boxes_stats AS
SELECT
    mb.id,
    mb.topic,
    mb.memory_count,
    mb.pheromone_score,
    COUNT(tl.id) as trace_link_count,
    mb.updated_at
FROM memory_boxes mb
LEFT JOIN trace_links tl ON mb.id = tl.source_box_id OR mb.id = tl.target_box_id
WHERE mb.is_active = TRUE
GROUP BY mb.id, mb.topic, mb.memory_count, mb.pheromone_score, mb.updated_at
ORDER BY mb.pheromone_score DESC;

-- =============================================================================
-- Initial Data (Optional)
-- =============================================================================

-- Insert a welcome message
INSERT INTO wisdom (wisdom, category, pheromone_score)
VALUES ('Welcome to Persistent AI Memory! Your memories will grow stronger with use through pheromone learning.', 'system', 15.0)
ON CONFLICT DO NOTHING;

-- =============================================================================
-- Grants and Permissions
-- =============================================================================

-- Grant permissions to current user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO CURRENT_USER;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO CURRENT_USER;

-- =============================================================================
-- Schema Complete!
-- =============================================================================

-- Verify setup
DO $$
DECLARE
    table_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_type = 'BASE TABLE';

    RAISE NOTICE '✅ Schema created successfully!';
    RAISE NOTICE '   Tables created: %', table_count;
    RAISE NOTICE '   Ready for use with RLM + Mempheromone';
END $$;
