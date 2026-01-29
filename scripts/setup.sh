#!/bin/bash
set -e

# Persistent AI Memory: RLM + Mempheromone Setup Script
# This script sets up the mempheromone database and RLM plugin

echo "=================================================="
echo "Persistent AI Memory Setup"
echo "=================================================="
echo ""

# Check prerequisites
echo "Checking prerequisites..."

# Check PostgreSQL
if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL not found. Please install PostgreSQL 14+ first:"
    echo "   Ubuntu/Debian: sudo apt-get install postgresql postgresql-contrib"
    echo "   macOS: brew install postgresql"
    exit 1
fi
echo "✅ PostgreSQL found: $(psql --version | head -1)"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.9+ first"
    exit 1
fi
echo "✅ Python found: $(python3 --version)"

# Check pip
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 not found. Please install pip3 first"
    exit 1
fi
echo "✅ pip3 found"

echo ""
echo "=================================================="
echo "Step 1: Install Python Dependencies"
echo "=================================================="

if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt
    echo "✅ Python dependencies installed"
else
    echo "⚠️  requirements.txt not found, installing basic dependencies..."
    pip3 install psycopg2-binary sentence-transformers numpy
fi

echo ""
echo "=================================================="
echo "Step 2: Create Database"
echo "=================================================="

# Ask for database name
read -p "Database name [mempheromone]: " DB_NAME
DB_NAME=${DB_NAME:-mempheromone}

# Check if database exists
if psql -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
    echo "⚠️  Database '$DB_NAME' already exists"
    read -p "Drop and recreate? (y/N): " RECREATE
    if [ "$RECREATE" = "y" ] || [ "$RECREATE" = "Y" ]; then
        dropdb "$DB_NAME"
        echo "Dropped existing database"
    else
        echo "Using existing database"
    fi
fi

# Create database if it doesn't exist
if ! psql -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
    createdb "$DB_NAME"
    echo "✅ Created database '$DB_NAME'"
fi

echo ""
echo "=================================================="
echo "Step 3: Install pgvector Extension"
echo "=================================================="

psql -d "$DB_NAME" -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null || {
    echo "⚠️  pgvector extension not available"
    echo "    This is optional but recommended for semantic search"
    echo "    Install from: https://github.com/pgvector/pgvector"
}

echo ""
echo "=================================================="
echo "Step 4: Create Database Schema"
echo "=================================================="

if [ -f "schema/mempheromone_schema.sql" ]; then
    psql -d "$DB_NAME" -f schema/mempheromone_schema.sql
    echo "✅ Database schema created"
else
    echo "⚠️  schema/mempheromone_schema.sql not found"
    echo "    Creating minimal schema..."

    psql -d "$DB_NAME" <<EOF
-- Core tables (minimal setup)
CREATE TABLE IF NOT EXISTS debugging_facts (
    fact_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symptom TEXT NOT NULL,
    solution TEXT NOT NULL,
    pheromone_score FLOAT DEFAULT 10.0,
    search_count INTEGER DEFAULT 0,
    retrieval_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMP DEFAULT NOW(),
    first_seen TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS claude_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    problem TEXT NOT NULL,
    solution TEXT NOT NULL,
    pheromone_score FLOAT DEFAULT 10.0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS session_narratives (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    narrative TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS crystallization_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    insight TEXT NOT NULL,
    temperature FLOAT DEFAULT 0.0,
    amplitude FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS wisdom (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wisdom TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Memory boxes for topic-continuous memory
CREATE TABLE IF NOT EXISTS memory_boxes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic VARCHAR(255),
    memory_count INTEGER DEFAULT 0,
    pheromone_score FLOAT DEFAULT 10.0,
    is_active BOOLEAN DEFAULT TRUE,
    keywords TEXT[],
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS memory_box_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    box_id UUID REFERENCES memory_boxes(id) ON DELETE CASCADE,
    memory_type VARCHAR(50),
    memory_id UUID,
    added_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS trace_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_box_id UUID REFERENCES memory_boxes(id) ON DELETE CASCADE,
    target_box_id UUID REFERENCES memory_boxes(id) ON DELETE CASCADE,
    similarity_score FLOAT,
    linking_events TEXT[],
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_debugging_facts_pheromone ON debugging_facts(pheromone_score DESC);
CREATE INDEX IF NOT EXISTS idx_memory_boxes_pheromone ON memory_boxes(pheromone_score DESC);

EOF
    echo "✅ Minimal schema created"
fi

echo ""
echo "=================================================="
echo "Step 5: Install RLM Plugin"
echo "=================================================="

RLM_PLUGIN_DIR="$HOME/.claude/plugins/rlm-mempheromone"

if [ -d "$RLM_PLUGIN_DIR" ]; then
    echo "⚠️  RLM plugin already installed at $RLM_PLUGIN_DIR"
    read -p "Overwrite? (y/N): " OVERWRITE
    if [ "$OVERWRITE" = "y" ] || [ "$OVERWRITE" = "Y" ]; then
        rm -rf "$RLM_PLUGIN_DIR"
    else
        echo "Skipping plugin installation"
    fi
fi

if [ ! -d "$RLM_PLUGIN_DIR" ]; then
    mkdir -p "$HOME/.claude/plugins"
    cp -r rlm-plugin "$RLM_PLUGIN_DIR"
    chmod +x "$RLM_PLUGIN_DIR/hooks/"*.sh
    echo "✅ RLM plugin installed to $RLM_PLUGIN_DIR"
fi

echo ""
echo "=================================================="
echo "Step 6: Configure Database Connection"
echo "=================================================="

# Update connection string in export script
EXPORT_SCRIPT="$RLM_PLUGIN_DIR/scripts/mempheromone_export.py"
if [ -f "$EXPORT_SCRIPT" ]; then
    # Set database name in environment
    echo "Database connection will use: $DB_NAME"
    echo "To set permanently, add to your ~/.bashrc or ~/.zshrc:"
    echo "  export PGDATABASE=$DB_NAME"
fi

echo ""
echo "=================================================="
echo "Setup Complete! 🎉"
echo "=================================================="
echo ""
echo "Next steps:"
echo "1. Start using Claude Code - memory will load automatically"
echo "2. (Optional) Set up membox automation:"
echo "   crontab -e"
echo "   Add: 0 * * * * $(pwd)/scripts/membox_cron.sh"
echo ""
echo "3. Verify setup:"
echo "   psql -d $DB_NAME -c \"SELECT COUNT(*) FROM debugging_facts;\""
echo ""
echo "Documentation:"
echo "  - README.md - Main documentation"
echo "  - docs/RLM_WHITEPAPER.md - Technical deep dive"
echo "  - docs/MEMBOX_SETUP.md - Topic-continuous memory"
echo ""
echo "Your database: $DB_NAME"
echo "RLM plugin: $RLM_PLUGIN_DIR"
echo ""
echo "Happy coding! 🚀"
