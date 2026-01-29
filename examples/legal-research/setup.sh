#!/bin/bash
set -e

# Legal Hub Setup Script
# Sets up Legal Hub variant of mempheromone for legal research

echo "=================================================="
echo "Legal Hub Setup"
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

echo ""
echo "=================================================="
echo "Step 1: Create Database"
echo "=================================================="

# Database name
DB_NAME="legal_hub"

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

# Create database
if ! psql -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
    createdb "$DB_NAME"
    echo "✅ Created database '$DB_NAME'"
fi

echo ""
echo "=================================================="
echo "Step 2: Install pgvector Extension"
echo "=================================================="

psql -d "$DB_NAME" -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null || {
    echo "⚠️  pgvector extension not available (optional)"
}

echo ""
echo "=================================================="
echo "Step 3: Create Legal Hub Schema"
echo "=================================================="

psql -d "$DB_NAME" <<EOF
-- Legal cases table
CREATE TABLE IF NOT EXISTS legal_cases (
    case_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    citation VARCHAR(255),
    case_name TEXT NOT NULL,
    court VARCHAR(255),
    jurisdiction VARCHAR(100),
    decided_date DATE,
    summary TEXT,
    full_text TEXT,
    url TEXT,
    pheromone_score FLOAT DEFAULT 10.0,
    search_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    last_accessed TIMESTAMP DEFAULT NOW()
);

-- Citations between cases
CREATE TABLE IF NOT EXISTS case_citations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    citing_case_id UUID REFERENCES legal_cases(case_id) ON DELETE CASCADE,
    cited_case_id UUID REFERENCES legal_cases(case_id) ON DELETE CASCADE,
    citation_context TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Legal research notes
CREATE TABLE IF NOT EXISTS research_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID REFERENCES legal_cases(case_id) ON DELETE CASCADE,
    note TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_legal_cases_citation ON legal_cases(citation);
CREATE INDEX IF NOT EXISTS idx_legal_cases_court ON legal_cases(court);
CREATE INDEX IF NOT EXISTS idx_legal_cases_jurisdiction ON legal_cases(jurisdiction);
CREATE INDEX IF NOT EXISTS idx_legal_cases_pheromone ON legal_cases(pheromone_score DESC);
CREATE INDEX IF NOT EXISTS idx_case_citations_citing ON case_citations(citing_case_id);
CREATE INDEX IF NOT EXISTS idx_case_citations_cited ON case_citations(cited_case_id);

EOF

echo "✅ Legal Hub schema created"

echo ""
echo "=================================================="
echo "Step 4: CourtListener API Setup"
echo "=================================================="

echo ""
echo "To use CourtListener API (free):"
echo "1. Go to: https://www.courtlistener.com/"
echo "2. Sign up for free account"
echo "3. Go to Profile → API → Generate New API Token"
echo "4. Copy your token"
echo ""
read -p "Do you have your CourtListener API token? (y/N): " HAS_TOKEN

if [ "$HAS_TOKEN" = "y" ] || [ "$HAS_TOKEN" = "Y" ]; then
    read -p "Enter your CourtListener API token: " API_TOKEN

    # Save to environment
    echo "export COURTLISTENER_API_TOKEN=\"$API_TOKEN\"" >> ~/.bashrc
    echo "✅ API token saved to ~/.bashrc"
    echo "   Run: source ~/.bashrc"
else
    echo "⚠️  Skipping API token setup"
    echo "   You can set it later with:"
    echo "   export COURTLISTENER_API_TOKEN=\"your_token_here\""
fi

echo ""
echo "=================================================="
echo "Setup Complete! 🎉"
echo "=================================================="
echo ""
echo "Your Legal Hub is ready!"
echo ""
echo "Next steps:"
echo "1. Get CourtListener API token (if you haven't): https://www.courtlistener.com/"
echo "2. Import your first cases:"
echo "   See QUICKSTART.md for detailed instructions"
echo ""
echo "3. Test your setup:"
echo "   psql -d legal_hub -c \"SELECT COUNT(*) FROM legal_cases;\""
echo ""
echo "Documentation:"
echo "  - QUICKSTART.md (English) - 15-minute setup guide"
echo "  - INICIO_RAPIDO.md (Español) - Guía de configuración"
echo "  - ../../.ai/BUILD_LEGAL_HUB.md - Complete technical guide"
echo ""
echo "Database: legal_hub"
echo ""
echo "Happy researching! ⚖️"
