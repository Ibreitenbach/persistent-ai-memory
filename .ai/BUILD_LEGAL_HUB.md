# Build Legal Hub: AI Handoff Document

**Purpose**: Step-by-step instructions for AI agents to build a Legal Hub variant of the persistent-ai-memory system.

**Time Estimate**: 3-4 hours for complete setup

**Prerequisites**:
- Core mempheromone system installed (see `.ai/BUILD_CORE_SYSTEM.md`)
- RLM plugin configured (see `RLM_WHITEPAPER.md`)
- PostgreSQL + pgvector running
- Python 3.9+

---

## 1. Overview

Legal Hub extends the core memory system with legal research capabilities:
- **Case law storage** - Store and search court opinions
- **Citation tracking** - Build citation graphs between cases
- **Precedent analysis** - Find similar cases and relevant precedents
- **Jurisdictional filtering** - Search by court, date range, jurisdiction
- **Multi-source integration** - Federal courts, state courts, municipal ordinances

**Architecture**:
```
Core Memory System (mempheromone + RLM)
    ↓
Legal Schema Extensions (cases, citations, precedents)
    ↓
Legal MCP Tools (legal_case_search, citation_tracker, precedent_analyzer)
    ↓
Data Sources (CourtListener, PACER, Municipal/State APIs)
```

---

## 2. Data Sources & Credentials

### 2.1 Universal Sources (Same for Everyone)

#### CourtListener (Free API)
**What it provides**: Federal and state court opinions, dockets, audio recordings

**How to get free credentials**:
1. Go to https://www.courtlistener.com/
2. Create free account (Sign Up)
3. Navigate to Profile → API Tokens
4. Generate new API token
5. Save token: `COURTLISTENER_API_TOKEN=your_token_here`

**API Documentation**: https://www.courtlistener.com/api/rest-info/

**Rate Limits**: 5,000 requests/day (free tier)

**Example API Call**:
```bash
curl -H "Authorization: Token YOUR_TOKEN" \
  "https://www.courtlistener.com/api/rest/v3/search/?q=constitutional%20rights&type=o"
```

#### Federal Court Data (PACER)
**What it provides**: Federal court filings, dockets, case documents

**How to get access**:
1. Go to https://pacer.uscourts.gov/
2. Register for PACER account (free registration)
3. Add payment method (charges $0.10/page, first $30/quarter is free)
4. Get PACER credentials: username + password

**Cost**: Effectively free for moderate use ($30 free quarterly = ~300 pages)

**Note**: PACER doesn't have a REST API - requires web scraping or third-party tools

#### Free Law Project
**What it provides**: Free bulk downloads of court opinions

**How to access**:
1. Go to https://free.law/
2. Download bulk data: https://www.courtlistener.com/api/bulk-info/
3. No credentials needed for bulk downloads

**Data Format**: JSON files with case metadata + opinions

### 2.2 Jurisdictional Sources (Find Your Own)

**Principle**: Every jurisdiction has different systems. You need to find equivalent sources for your location.

#### Example: Oklahoma City + Oklahoma State

**Municipal (OKC)**:
- **Source**: Oklahoma City Municipal Court website
- **URL**: https://www.okc.gov/departments/municipal-court
- **Data Available**: Traffic citations, ordinance violations, public records
- **API**: None (requires web scraping or public records request)
- **Credentials**: Public records requests are free under Oklahoma Open Records Act

**State (Oklahoma)**:
- **Source**: Oklahoma State Courts Network (OSCN)
- **URL**: https://www.oscn.net/
- **Data Available**: State supreme court, court of appeals, district courts
- **API**: Limited (mostly web scraping)
- **How to Access**:
  1. Go to OSCN website
  2. Use "Case Search" feature
  3. No login required for public records
  4. Can scrape docket sheets and opinions

**State Legislature**:
- **Source**: Oklahoma Legislature website
- **URL**: http://www.oklegislature.gov/
- **Data Available**: Statutes, bills, legislative history
- **API**: None (web scraping)

#### How to Find Your Jurisdiction's Sources

**Step 1: Identify Your Courts**
```
Municipal Level → City/Town Court
County Level → County/District Court
State Level → State Supreme Court + Appeals Courts
Federal Level → District Court → Circuit Court → Supreme Court
```

**Step 2: Google Search Pattern**
```
"[City Name] municipal court records"
"[State Name] court records online"
"[State Name] judicial system case search"
"[County Name] court docket"
```

**Step 3: Check State Bar Association**
- Search: "[State] bar association"
- Look for "Legal Resources" or "Public Records"
- Often has links to court systems

**Step 4: Public Records Laws**
- Every state has open records laws (like Oklahoma's Open Records Act)
- Search: "[State] open records request"
- Municipal/state court records are usually public

**Step 5: Contact Clerk's Office**
- Call or email court clerk's office
- Ask: "How can I access public court records online?"
- Many have online portals or will email records for free

**Common Municipal Data Sources**:
- City website → "Municipal Court" section
- County Clerk websites
- State judicial system websites
- Third-party legal data aggregators

**Example Search Process (for Denver, CO)**:
1. Google: "Denver municipal court records"
   - Result: https://www.denvergov.org/Government/Agencies-Departments-Offices/Agencies-Departments-Offices-Directory/County-Court
2. Google: "Colorado state court records"
   - Result: https://www.courts.state.co.us/ (statewide system)
3. Check if API exists: "Colorado courts API"
   - Result: Usually no API, need to scrape or request bulk data
4. Check state bar: https://www.cobar.org/
   - May have links to legal research databases

### 2.3 Free Legal Research Databases

#### Justia
- **URL**: https://www.justia.com/
- **What it provides**: Free case law, statutes, regulations
- **Coverage**: Federal + all 50 states
- **API**: Limited (mostly web scraping)
- **Cost**: Free

#### Google Scholar (Legal)
- **URL**: https://scholar.google.com/ (select "Case law")
- **What it provides**: Federal and state case law
- **Coverage**: Comprehensive
- **API**: None (unofficial scraping possible)
- **Cost**: Free

#### Cornell LII (Legal Information Institute)
- **URL**: https://www.law.cornell.edu/
- **What it provides**: U.S. Code, CFR, Supreme Court opinions
- **Coverage**: Federal law
- **API**: None
- **Cost**: Free

---

## 3. Database Schema Extensions

### 3.1 Core Tables

Add these tables to your mempheromone database:

```sql
-- Legal cases
CREATE TABLE legal_cases (
    case_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Case identification
    citation VARCHAR(500),                    -- e.g., "410 U.S. 113"
    case_name TEXT NOT NULL,                  -- e.g., "Roe v. Wade"
    docket_number VARCHAR(200),               -- e.g., "70-18"

    -- Court information
    court_name VARCHAR(200),                  -- e.g., "Supreme Court of the United States"
    court_level VARCHAR(50),                  -- federal, state, municipal
    jurisdiction VARCHAR(100),                -- e.g., "Oklahoma", "10th Circuit"

    -- Dates
    filed_date DATE,
    decided_date DATE,

    -- Content
    opinion_text TEXT,                        -- Full text of opinion
    summary TEXT,                             -- LLM-generated summary
    holding TEXT,                             -- Legal holding

    -- Classification
    practice_areas VARCHAR(100)[],            -- e.g., ["constitutional", "criminal"]
    outcome VARCHAR(50),                      -- plaintiff, defendant, affirmed, reversed

    -- Source tracking
    source VARCHAR(50),                       -- courtlistener, pacer, oscn, etc.
    source_url TEXT,
    source_id VARCHAR(200),                   -- ID in source system

    -- Pheromone scoring (reuse pattern)
    pheromone_score FLOAT DEFAULT 10.0,
    access_count INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Citation graph
CREATE TABLE case_citations (
    citation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Relationship
    citing_case_id UUID REFERENCES legal_cases(case_id) ON DELETE CASCADE,
    cited_case_id UUID REFERENCES legal_cases(case_id) ON DELETE CASCADE,

    -- Citation metadata
    citation_type VARCHAR(50),                -- precedent, distinguished, overruled
    citation_context TEXT,                    -- Surrounding text
    treatment VARCHAR(50),                    -- positive, negative, neutral

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW()
);

-- Legal research sessions (tracks what you searched)
CREATE TABLE legal_research_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Query
    research_question TEXT NOT NULL,
    keywords TEXT[],
    jurisdiction VARCHAR(100),
    practice_area VARCHAR(100),

    -- Results
    cases_found INTEGER,
    relevant_cases UUID[],                    -- Array of case_ids

    -- Feedback
    useful BOOLEAN,
    notes TEXT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for fast retrieval
CREATE INDEX idx_legal_cases_citation ON legal_cases(citation);
CREATE INDEX idx_legal_cases_court ON legal_cases(court_name);
CREATE INDEX idx_legal_cases_jurisdiction ON legal_cases(jurisdiction);
CREATE INDEX idx_legal_cases_decided_date ON legal_cases(decided_date);
CREATE INDEX idx_legal_cases_pheromone ON legal_cases(pheromone_score DESC);
CREATE INDEX idx_legal_cases_practice_areas ON legal_cases USING GIN(practice_areas);

-- Citation graph indexes
CREATE INDEX idx_citations_citing ON case_citations(citing_case_id);
CREATE INDEX idx_citations_cited ON case_citations(cited_case_id);

-- Composite index for common queries
CREATE INDEX idx_legal_cases_jurisdiction_date
    ON legal_cases(jurisdiction, decided_date DESC);
```

### 3.2 Vector Embeddings for Cases

```sql
-- Case embeddings (semantic search)
CREATE TABLE legal_case_embeddings (
    case_id UUID PRIMARY KEY REFERENCES legal_cases(case_id) ON DELETE CASCADE,
    embedding vector(384),                    -- sentence-transformers/all-MiniLM-L6-v2
    embedding_model VARCHAR(100) DEFAULT 'all-MiniLM-L6-v2',
    created_at TIMESTAMP DEFAULT NOW()
);

-- HNSW index for fast similarity search
CREATE INDEX ON legal_case_embeddings USING hnsw (embedding vector_cosine_ops);
```

### 3.3 Pheromone Reinforcement for Legal Research

```sql
-- Reinforce useful cases
CREATE OR REPLACE FUNCTION reinforce_legal_case(
    p_case_id UUID,
    p_successful BOOLEAN
) RETURNS VOID AS $$
BEGIN
    UPDATE legal_cases
    SET
        access_count = access_count + 1,
        pheromone_score = LEAST(20.0, pheromone_score +
            CASE WHEN p_successful THEN 0.5 ELSE -0.3 END),
        updated_at = NOW()
    WHERE case_id = p_case_id;
END;
$$ LANGUAGE plpgsql;
```

---

## 4. Data Ingestion Scripts

### 4.1 CourtListener Ingestion

**File**: `scripts/ingest_courtlistener.py`

```python
#!/usr/bin/env python3
"""
Ingest cases from CourtListener API into legal_cases table.
"""

import os
import requests
import psycopg2
import psycopg2.extras
from datetime import datetime

COURTLISTENER_API_TOKEN = os.getenv('COURTLISTENER_API_TOKEN')
COURTLISTENER_BASE_URL = 'https://www.courtlistener.com/api/rest/v3'

def get_db_connection():
    """Get PostgreSQL connection."""
    return psycopg2.connect(
        host=os.getenv('PGHOST', 'localhost'),
        port=os.getenv('PGPORT', '5432'),
        database=os.getenv('PGDATABASE', 'mempheromone'),
        user=os.getenv('PGUSER', 'ike'),
        password=os.getenv('PGPASSWORD', '')
    )

def search_opinions(query, court=None, jurisdiction=None, limit=100):
    """
    Search CourtListener for opinions.

    Args:
        query: Search query (e.g., "constitutional rights")
        court: Filter by court (e.g., "scotus" for Supreme Court)
        jurisdiction: Filter by jurisdiction (e.g., "ca" for California)
        limit: Max results (default 100)

    Returns:
        List of opinion dicts
    """
    headers = {'Authorization': f'Token {COURTLISTENER_API_TOKEN}'}

    params = {
        'q': query,
        'type': 'o',  # opinions
        'order_by': 'dateFiled desc'
    }

    if court:
        params['court'] = court
    if jurisdiction:
        params['court_jurisdiction'] = jurisdiction

    response = requests.get(
        f'{COURTLISTENER_BASE_URL}/search/',
        headers=headers,
        params=params
    )

    response.raise_for_status()
    data = response.json()

    results = []
    for result in data.get('results', [])[:limit]:
        # Fetch full opinion detail
        opinion_id = result.get('id')
        if opinion_id:
            opinion = get_opinion_detail(opinion_id)
            if opinion:
                results.append(opinion)

    return results

def get_opinion_detail(opinion_id):
    """Fetch full opinion details."""
    headers = {'Authorization': f'Token {COURTLISTENER_API_TOKEN}'}

    response = requests.get(
        f'{COURTLISTENER_BASE_URL}/opinions/{opinion_id}/',
        headers=headers
    )

    if response.status_code == 200:
        return response.json()
    return None

def store_case(conn, opinion):
    """Store case in legal_cases table."""
    with conn.cursor() as cur:
        # Extract data from CourtListener opinion
        case_name = opinion.get('case_name', '')
        citation = opinion.get('citation', '')
        docket_number = opinion.get('docket_number', '')
        court_name = opinion.get('court', {}).get('name', '')
        filed_date = opinion.get('date_filed')
        opinion_text = opinion.get('plain_text', '') or opinion.get('html', '')

        # Determine jurisdiction from court
        jurisdiction = extract_jurisdiction(court_name)

        # Check if already exists
        cur.execute("""
            SELECT case_id FROM legal_cases
            WHERE citation = %s OR (case_name = %s AND court_name = %s)
        """, (citation, case_name, court_name))

        if cur.fetchone():
            print(f"  ⚠️  Case already exists: {case_name}")
            return None

        # Insert case
        cur.execute("""
            INSERT INTO legal_cases
            (case_name, citation, docket_number, court_name, court_level,
             jurisdiction, filed_date, decided_date, opinion_text,
             source, source_url, source_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING case_id
        """, (
            case_name,
            citation,
            docket_number,
            court_name,
            determine_court_level(court_name),
            jurisdiction,
            filed_date,
            filed_date,  # CourtListener uses filed_date
            opinion_text[:100000],  # Limit to 100k chars
            'courtlistener',
            f'https://www.courtlistener.com{opinion.get("absolute_url", "")}',
            str(opinion.get('id'))
        ))

        case_id = cur.fetchone()[0]
        conn.commit()

        print(f"  ✓ Stored: {case_name} ({citation})")
        return case_id

def extract_jurisdiction(court_name):
    """Extract jurisdiction from court name."""
    # Simple heuristic - can be improved
    if 'United States' in court_name or 'Supreme Court' in court_name:
        return 'federal'

    # Look for state abbreviations
    import re
    state_match = re.search(r'\b([A-Z]{2})\b', court_name)
    if state_match:
        return state_match.group(1)

    return 'unknown'

def determine_court_level(court_name):
    """Determine court level from name."""
    court_lower = court_name.lower()

    if 'supreme court' in court_lower:
        return 'supreme'
    elif 'appellate' in court_lower or 'appeal' in court_lower:
        return 'appellate'
    elif 'district' in court_lower or 'trial' in court_lower:
        return 'district'
    elif 'municipal' in court_lower or 'city' in court_lower:
        return 'municipal'

    return 'unknown'

def main():
    """CLI interface for CourtListener ingestion."""
    import argparse

    parser = argparse.ArgumentParser(description='Ingest cases from CourtListener')
    parser.add_argument('query', help='Search query (e.g., "constitutional rights")')
    parser.add_argument('--court', help='Filter by court (e.g., scotus)')
    parser.add_argument('--jurisdiction', help='Filter by jurisdiction (e.g., ca)')
    parser.add_argument('--limit', type=int, default=100, help='Max results (default: 100)')

    args = parser.parse_args()

    if not COURTLISTENER_API_TOKEN:
        print("❌ Error: COURTLISTENER_API_TOKEN not set")
        print("   Export your token: export COURTLISTENER_API_TOKEN=your_token")
        return

    print(f"🔍 Searching CourtListener: {args.query}")

    # Search opinions
    opinions = search_opinions(
        args.query,
        court=args.court,
        jurisdiction=args.jurisdiction,
        limit=args.limit
    )

    print(f"📊 Found {len(opinions)} opinions")

    # Store in database
    conn = get_db_connection()
    stored = 0

    for opinion in opinions:
        case_id = store_case(conn, opinion)
        if case_id:
            stored += 1

    conn.close()

    print(f"\n{'='*60}")
    print(f"✅ Ingestion Complete")
    print(f"   Stored: {stored} new cases")
    print(f"   Skipped: {len(opinions) - stored} duplicates")

if __name__ == '__main__':
    main()
```

**Usage**:
```bash
# Set API token
export COURTLISTENER_API_TOKEN=your_token_here

# Search and ingest
python3 scripts/ingest_courtlistener.py "Fourth Amendment search seizure" --limit 50
python3 scripts/ingest_courtlistener.py "contract law" --jurisdiction ok --limit 100
python3 scripts/ingest_courtlistener.py "constitutional rights" --court scotus --limit 25
```

### 4.2 State Court Scraper Template

**File**: `scripts/ingest_state_courts.py`

```python
#!/usr/bin/env python3
"""
Template for scraping state court systems.
Customize for your jurisdiction (example: Oklahoma OSCN).
"""

import requests
from bs4 import BeautifulSoup
import psycopg2
from datetime import datetime

def scrape_oscn_case(case_number, county='Oklahoma'):
    """
    Scrape Oklahoma State Courts Network (OSCN) for case.

    Args:
        case_number: Docket number (e.g., "CF-2020-123")
        county: County name (default: Oklahoma)

    Returns:
        Dict with case data or None
    """
    # OSCN search URL
    url = f'https://www.oscn.net/dockets/GetCaseInformation.aspx'

    params = {
        'db': county.lower(),
        'number': case_number
    }

    response = requests.get(url, params=params)

    if response.status_code != 200:
        return None

    # Parse HTML
    soup = BeautifulSoup(response.text, 'html.parser')

    # Extract case details (customize based on HTML structure)
    case_data = {
        'case_name': extract_case_name(soup),
        'docket_number': case_number,
        'court_name': f'{county} County District Court',
        'jurisdiction': 'Oklahoma',
        'filed_date': extract_filed_date(soup),
        'case_type': extract_case_type(soup),
        'docket_text': soup.get_text(),
        'source': 'oscn',
        'source_url': response.url
    }

    return case_data

def extract_case_name(soup):
    """Extract case name from HTML (customize for your court)."""
    # Example: Look for <h2> with case name
    h2 = soup.find('h2')
    if h2:
        return h2.get_text().strip()
    return 'Unknown'

def extract_filed_date(soup):
    """Extract filing date (customize for your court)."""
    # Example: Look for "Filed: MM/DD/YYYY" pattern
    import re
    text = soup.get_text()
    match = re.search(r'Filed:\s*(\d{1,2}/\d{1,2}/\d{4})', text)
    if match:
        date_str = match.group(1)
        return datetime.strptime(date_str, '%m/%d/%Y').date()
    return None

def extract_case_type(soup):
    """Extract case type (criminal, civil, etc.)."""
    # Example: Look for case type in docket number prefix
    # CF = Criminal Felony, CM = Civil, etc.
    return 'unknown'

# Similar pattern for other state courts:
# - Modify URL structure
# - Customize HTML parsing
# - Add authentication if needed

def main():
    """CLI interface for state court scraping."""
    import argparse

    parser = argparse.ArgumentParser(description='Scrape state court records')
    parser.add_argument('case_number', help='Docket number')
    parser.add_argument('--county', default='Oklahoma', help='County name')
    parser.add_argument('--state', default='oklahoma', help='State (customize scraper)')

    args = parser.parse_args()

    if args.state == 'oklahoma':
        case_data = scrape_oscn_case(args.case_number, args.county)
        if case_data:
            print(f"✓ Found: {case_data['case_name']}")
            print(f"  Docket: {case_data['docket_number']}")
            print(f"  Filed: {case_data['filed_date']}")
        else:
            print(f"✗ Case not found: {args.case_number}")
    else:
        print(f"⚠️  State '{args.state}' not implemented")
        print("   Customize scrape_state_court() for your jurisdiction")

if __name__ == '__main__':
    main()
```

**Usage**:
```bash
# Scrape Oklahoma case
python3 scripts/ingest_state_courts.py CF-2020-123 --county Oklahoma --state oklahoma

# For your jurisdiction:
# 1. Find your state court website
# 2. Analyze HTML structure
# 3. Customize extract_* functions
# 4. Add new state handler
```

---

## 5. MCP Server Tools

### 5.1 Legal Case Search Tool

**File**: `mcp-server/src/tools/legal_case_search.ts`

```typescript
import { z } from 'zod';
import { Pool } from 'pg';

const LegalCaseSearchSchema = z.object({
  query: z.string().describe('Legal research question or keywords'),
  jurisdiction: z.string().optional().describe('Filter by jurisdiction (e.g., "Oklahoma", "federal")'),
  court: z.string().optional().describe('Filter by court name'),
  practice_area: z.string().optional().describe('Practice area (e.g., "constitutional", "criminal")'),
  start_date: z.string().optional().describe('Start date (YYYY-MM-DD)'),
  end_date: z.string().optional().describe('End date (YYYY-MM-DD)'),
  limit: z.number().default(10).describe('Max results (default: 10)')
});

export async function legal_case_search(
  args: z.infer<typeof LegalCaseSearchSchema>,
  pool: Pool
): Promise<string> {
  const { query, jurisdiction, court, practice_area, start_date, end_date, limit } = args;

  // Build WHERE clause
  const conditions: string[] = ['TRUE'];
  const params: any[] = [];
  let paramCount = 0;

  if (jurisdiction) {
    paramCount++;
    conditions.push(`jurisdiction ILIKE $${paramCount}`);
    params.push(`%${jurisdiction}%`);
  }

  if (court) {
    paramCount++;
    conditions.push(`court_name ILIKE $${paramCount}`);
    params.push(`%${court}%`);
  }

  if (practice_area) {
    paramCount++;
    conditions.push(`$${paramCount} = ANY(practice_areas)`);
    params.push(practice_area);
  }

  if (start_date) {
    paramCount++;
    conditions.push(`decided_date >= $${paramCount}`);
    params.push(start_date);
  }

  if (end_date) {
    paramCount++;
    conditions.push(`decided_date <= $${paramCount}`);
    params.push(end_date);
  }

  // Full-text search on case_name, opinion_text, summary
  paramCount++;
  conditions.push(`(
    case_name ILIKE $${paramCount} OR
    opinion_text ILIKE $${paramCount} OR
    summary ILIKE $${paramCount}
  )`);
  params.push(`%${query}%`);

  paramCount++;
  params.push(limit);

  const sql = `
    SELECT
      case_id,
      case_name,
      citation,
      court_name,
      jurisdiction,
      decided_date,
      summary,
      pheromone_score,
      access_count,
      source_url
    FROM legal_cases
    WHERE ${conditions.join(' AND ')}
    ORDER BY pheromone_score DESC, decided_date DESC
    LIMIT $${paramCount}
  `;

  const result = await pool.query(sql, params);

  if (result.rows.length === 0) {
    return `No cases found for query: "${query}"`;
  }

  // Format results
  let output = `Found ${result.rows.length} cases:\n\n`;

  for (const row of result.rows) {
    output += `${row.case_name}\n`;
    output += `  Citation: ${row.citation || 'N/A'}\n`;
    output += `  Court: ${row.court_name}\n`;
    output += `  Decided: ${row.decided_date?.toISOString().split('T')[0] || 'N/A'}\n`;
    output += `  Jurisdiction: ${row.jurisdiction}\n`;
    output += `  Pheromone: ${row.pheromone_score.toFixed(1)}\n`;
    if (row.summary) {
      output += `  Summary: ${row.summary.substring(0, 200)}...\n`;
    }
    output += `  URL: ${row.source_url || 'N/A'}\n`;
    output += '\n';
  }

  return output;
}

export const legal_case_search_tool = {
  name: 'legal_case_search',
  description: 'Search legal cases by keywords, jurisdiction, court, practice area, and date range',
  inputSchema: LegalCaseSearchSchema
};
```

### 5.2 Citation Tracker Tool

**File**: `mcp-server/src/tools/citation_tracker.ts`

```typescript
import { z } from 'zod';
import { Pool } from 'pg';

const CitationTrackerSchema = z.object({
  case_id: z.string().describe('UUID of the case to track citations for'),
  direction: z.enum(['citing', 'cited']).default('citing').describe('Direction: "citing" (cases citing this one) or "cited" (cases this one cites)'),
  limit: z.number().default(20).describe('Max results (default: 20)')
});

export async function citation_tracker(
  args: z.infer<typeof CitationTrackerSchema>,
  pool: Pool
): Promise<string> {
  const { case_id, direction, limit } = args;

  // Get base case info
  const caseResult = await pool.query(`
    SELECT case_name, citation, court_name
    FROM legal_cases
    WHERE case_id = $1
  `, [case_id]);

  if (caseResult.rows.length === 0) {
    return `Case not found: ${case_id}`;
  }

  const baseCase = caseResult.rows[0];

  // Get citations
  let sql: string;
  if (direction === 'citing') {
    sql = `
      SELECT
        lc.case_id,
        lc.case_name,
        lc.citation,
        lc.court_name,
        lc.decided_date,
        cc.citation_type,
        cc.treatment
      FROM case_citations cc
      JOIN legal_cases lc ON cc.citing_case_id = lc.case_id
      WHERE cc.cited_case_id = $1
      ORDER BY lc.decided_date DESC
      LIMIT $2
    `;
  } else {
    sql = `
      SELECT
        lc.case_id,
        lc.case_name,
        lc.citation,
        lc.court_name,
        lc.decided_date,
        cc.citation_type,
        cc.treatment
      FROM case_citations cc
      JOIN legal_cases lc ON cc.cited_case_id = lc.case_id
      WHERE cc.citing_case_id = $1
      ORDER BY lc.decided_date DESC
      LIMIT $2
    `;
  }

  const result = await pool.query(sql, [case_id, limit]);

  let output = `${baseCase.case_name} (${baseCase.citation})\n`;
  output += `${direction === 'citing' ? 'Cited by' : 'Cites'}: ${result.rows.length} cases\n\n`;

  for (const row of result.rows) {
    output += `${row.case_name}\n`;
    output += `  Citation: ${row.citation || 'N/A'}\n`;
    output += `  Court: ${row.court_name}\n`;
    output += `  Decided: ${row.decided_date?.toISOString().split('T')[0] || 'N/A'}\n`;
    output += `  Type: ${row.citation_type || 'N/A'}\n`;
    output += `  Treatment: ${row.treatment || 'N/A'}\n`;
    output += '\n';
  }

  return output;
}

export const citation_tracker_tool = {
  name: 'citation_tracker',
  description: 'Track citations for a legal case (cases citing this one, or cases this one cites)',
  inputSchema: CitationTrackerSchema
};
```

### 5.3 Precedent Analyzer Tool

**File**: `mcp-server/src/tools/precedent_analyzer.ts`

```typescript
import { z } from 'zod';
import { Pool } from 'pg';

const PrecedentAnalyzerSchema = z.object({
  query: z.string().describe('Legal issue or facts to find precedents for'),
  jurisdiction: z.string().optional().describe('Limit to jurisdiction'),
  min_pheromone: z.number().default(10.0).describe('Minimum pheromone score (default: 10.0)'),
  limit: z.number().default(10).describe('Max results (default: 10)')
});

export async function precedent_analyzer(
  args: z.infer<typeof PrecedentAnalyzerSchema>,
  pool: Pool
): Promise<string> {
  const { query, jurisdiction, min_pheromone, limit } = args;

  // Build WHERE clause
  const conditions: string[] = [`pheromone_score >= $1`];
  const params: any[] = [min_pheromone];
  let paramCount = 1;

  if (jurisdiction) {
    paramCount++;
    conditions.push(`jurisdiction ILIKE $${paramCount}`);
    params.push(`%${jurisdiction}%`);
  }

  // Full-text search
  paramCount++;
  conditions.push(`(
    case_name ILIKE $${paramCount} OR
    opinion_text ILIKE $${paramCount} OR
    summary ILIKE $${paramCount} OR
    holding ILIKE $${paramCount}
  )`);
  params.push(`%${query}%`);

  paramCount++;
  params.push(limit);

  const sql = `
    SELECT
      case_id,
      case_name,
      citation,
      court_name,
      jurisdiction,
      decided_date,
      holding,
      summary,
      pheromone_score,
      access_count
    FROM legal_cases
    WHERE ${conditions.join(' AND ')}
    ORDER BY
      -- Prioritize: higher pheromone, recent dates, higher courts
      pheromone_score DESC,
      CASE
        WHEN court_level = 'supreme' THEN 1
        WHEN court_level = 'appellate' THEN 2
        WHEN court_level = 'district' THEN 3
        ELSE 4
      END,
      decided_date DESC
    LIMIT $${paramCount}
  `;

  const result = await pool.query(sql, params);

  if (result.rows.length === 0) {
    return `No precedents found for: "${query}"`;
  }

  let output = `Found ${result.rows.length} precedents for: "${query}"\n\n`;

  for (const row of result.rows) {
    output += `${row.case_name}\n`;
    output += `  Citation: ${row.citation || 'N/A'}\n`;
    output += `  Court: ${row.court_name}\n`;
    output += `  Decided: ${row.decided_date?.toISOString().split('T')[0] || 'N/A'}\n`;
    output += `  Jurisdiction: ${row.jurisdiction}\n`;
    output += `  Pheromone: ${row.pheromone_score.toFixed(1)} (accessed ${row.access_count} times)\n`;

    if (row.holding) {
      output += `  Holding: ${row.holding.substring(0, 300)}...\n`;
    }

    if (row.summary) {
      output += `  Summary: ${row.summary.substring(0, 300)}...\n`;
    }

    output += '\n';
  }

  return output;
}

export const precedent_analyzer_tool = {
  name: 'precedent_analyzer',
  description: 'Find relevant legal precedents for a given issue or fact pattern',
  inputSchema: PrecedentAnalyzerSchema
};
```

---

## 6. RLM Integration

### 6.1 Legal Hub RLM Export

Modify `~/.claude/plugins/rlm-prototype/scripts/mempheromone_export.py` to include legal cases:

```python
def export_legal_cases(conn, limit=50, min_pheromone=12.0):
    """Export high-quality legal cases for RLM awakening."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT
                case_name,
                citation,
                court_name,
                decided_date,
                jurisdiction,
                holding,
                summary,
                pheromone_score,
                access_count
            FROM legal_cases
            WHERE pheromone_score >= %s
            ORDER BY pheromone_score DESC, decided_date DESC
            LIMIT %s
        """, (min_pheromone, limit))

        cases = []
        for row in cur.fetchall():
            cases.append({
                'case': row['case_name'],
                'citation': row['citation'],
                'court': row['court_name'],
                'date': row['decided_date'].isoformat() if row['decided_date'] else None,
                'jurisdiction': row['jurisdiction'],
                'holding': row['holding'],
                'summary': row['summary'],
                'pheromone': row['pheromone_score'],
                'accessed': row['access_count']
            })

        return cases

# In main():
if args.include_legal:
    legal_cases = export_legal_cases(conn, limit=50, min_pheromone=args.min_score)

    output += f"\n{'='*80}\n"
    output += f"## Legal Precedents (High-Quality Cases)\n"
    output += f"{'='*80}\n\n"
    output += f"{len(legal_cases)} cases with pheromone >= {args.min_score}:\n\n"

    for i, case in enumerate(legal_cases, 1):
        output += f"{i}. {case['case']}\n"
        output += f"   {case['citation']} | {case['court']} | {case['date']}\n"
        output += f"   Jurisdiction: {case['jurisdiction']} | ψ={case['pheromone']:.1f}\n"
        if case['holding']:
            output += f"   Holding: {case['holding'][:200]}...\n"
        output += '\n'
```

**Usage**:
```bash
python3 ~/.claude/plugins/rlm-prototype/scripts/mempheromone_export.py \
    --include-legal \
    --output /tmp/legal_hub_context.txt
```

---

## 7. Validation & Testing

### 7.1 Verify Database Setup

```sql
-- Check tables exist
\dt legal*

-- Count cases
SELECT COUNT(*) as total_cases FROM legal_cases;

-- Check pheromone distribution
SELECT
    CASE
        WHEN pheromone_score >= 15 THEN 'Expert (15+)'
        WHEN pheromone_score >= 10 THEN 'Solid (10-14)'
        WHEN pheromone_score >= 5 THEN 'Unproven (5-9)'
        ELSE 'Low (<5)'
    END as tier,
    COUNT(*) as count
FROM legal_cases
GROUP BY tier
ORDER BY MIN(pheromone_score) DESC;

-- Sample cases
SELECT case_name, citation, jurisdiction, pheromone_score
FROM legal_cases
ORDER BY pheromone_score DESC
LIMIT 10;
```

### 7.2 Test Data Ingestion

```bash
# Test CourtListener ingestion
export COURTLISTENER_API_TOKEN=your_token
python3 scripts/ingest_courtlistener.py "Fourth Amendment" --limit 10

# Verify ingestion
psql -U ike -d mempheromone -c "SELECT COUNT(*) FROM legal_cases WHERE source='courtlistener';"
```

### 7.3 Test MCP Tools

```bash
# Test legal case search
# (via Claude Code or MCP client)
legal_case_search(query="constitutional rights", jurisdiction="Oklahoma", limit=5)

# Test citation tracker
# (get a case_id first)
citation_tracker(case_id="...", direction="citing", limit=10)

# Test precedent analyzer
precedent_analyzer(query="unreasonable search and seizure", jurisdiction="federal")
```

---

## 8. Expected Results

After successful setup, you should have:

✅ **Database**:
- `legal_cases` table with cases from CourtListener
- `case_citations` table tracking citation graph
- `legal_case_embeddings` for semantic search
- Pheromone scores tracking case usefulness

✅ **Data**:
- Federal cases from CourtListener
- State/municipal cases from your jurisdiction (if scraped)
- Citation relationships between cases
- Embeddings for semantic search

✅ **MCP Tools**:
- `legal_case_search` - Search cases by keywords, jurisdiction, court
- `citation_tracker` - Track citations for a case
- `precedent_analyzer` - Find relevant precedents

✅ **RLM Integration**:
- High-quality cases (pheromone >= 12) load at session start
- Claude can reference precedents from memory
- No retrieval delay for loaded cases

---

## 9. Next Steps

### 9.1 Add Your Jurisdiction

1. Find your municipal/state court website
2. Analyze HTML structure
3. Create scraper in `scripts/ingest_YOUR_STATE.py`
4. Run scraper to populate database
5. Verify with `SELECT * FROM legal_cases WHERE jurisdiction='YOUR_STATE'`

### 9.2 Enhance with LLM Summarization

Add script to generate summaries for cases without them:

```python
# scripts/summarize_cases.py
for case in get_cases_without_summary():
    summary = call_llm(f"Summarize this legal opinion:\n\n{case.opinion_text}")
    update_case_summary(case.id, summary)
```

### 9.3 Build Citation Graph

Add script to extract citations from opinion text:

```python
# scripts/extract_citations.py
for case in get_all_cases():
    citations = extract_citations_from_text(case.opinion_text)
    for citation in citations:
        cited_case = find_case_by_citation(citation)
        if cited_case:
            insert_citation(citing=case.id, cited=cited_case.id)
```

---

## 10. Troubleshooting

### Issue: CourtListener API 429 (Rate Limit)
**Solution**: Free tier allows 5,000 requests/day. If exceeded:
- Wait 24 hours for reset
- Upgrade to paid tier ($50/month for 50,000 requests/day)
- Batch requests and run overnight

### Issue: State Court Scraper Fails
**Solution**:
- Court websites change frequently
- Update HTML selectors in scraper
- Use browser dev tools to inspect current structure
- Consider using Selenium for JavaScript-heavy sites

### Issue: No Cases in Database
**Solution**:
- Check API token: `echo $COURTLISTENER_API_TOKEN`
- Verify database connection: `psql -U ike -d mempheromone -c "\dt legal*"`
- Run test query manually in browser
- Check ingestion script logs for errors

### Issue: Pheromone Scores Not Updating
**Solution**:
- Verify reinforcement function exists: `\df reinforce_legal_case`
- Check MCP tool is calling reinforcement
- Enable silent observer for auto-reinforcement

---

## 11. Customization Guide

### For Different Practice Areas

**Example: Real Estate Law**

1. **Add practice area filter**:
```sql
ALTER TABLE legal_cases ADD COLUMN IF NOT EXISTS practice_areas VARCHAR(100)[];
UPDATE legal_cases SET practice_areas = ARRAY['real_estate']
WHERE case_name ILIKE '%property%' OR case_name ILIKE '%landlord%';
```

2. **Create specialized tool**:
```typescript
// mcp-server/src/tools/real_estate_precedents.ts
export async function real_estate_precedents(args, pool) {
  return precedent_analyzer({
    ...args,
    practice_area: 'real_estate'
  }, pool);
}
```

### For Different Jurisdictions

**Example: California**

1. **Add California court scraper**:
```python
# scripts/ingest_california.py
def scrape_california_courts(case_number):
    # California Courts website
    url = 'https://www.courts.ca.gov/...'
    # Customize for California HTML structure
```

2. **Update jurisdiction filters**:
```sql
-- California-specific queries
SELECT * FROM legal_cases WHERE jurisdiction = 'CA';
```

---

## 12. Success Criteria

✅ **Minimum (Must achieve)**:
- Database tables created without errors
- At least 100 cases ingested from CourtListener
- MCP tools respond with valid results
- RLM export includes legal cases

✅ **Strong**:
- 500+ cases from multiple sources
- Citation graph with 1,000+ relationships
- Pheromone learning working (scores update with usage)
- Your jurisdiction's cases included

✅ **Exceptional**:
- 10,000+ cases across federal + state + municipal
- Embeddings for semantic search
- LLM-generated summaries for all cases
- Full citation graph with treatment signals
- Silent observer auto-reinforcing useful precedents

---

## 13. Resources

**Legal Data Sources**:
- CourtListener: https://www.courtlistener.com/
- Free Law Project: https://free.law/
- Justia: https://www.justia.com/
- Google Scholar: https://scholar.google.com/ (Case law)
- Cornell LII: https://www.law.cornell.edu/

**State Court Directories**:
- NCSC (National Center for State Courts): https://www.ncsc.org/information-and-resources/state-court-websites
- State Bar Associations: Search "[State] bar association"

**API Documentation**:
- CourtListener API: https://www.courtlistener.com/api/rest-info/
- PACER API: https://pacer.uscourts.gov/help (limited)

**Tutorials**:
- Web scraping with BeautifulSoup: https://www.crummy.com/software/BeautifulSoup/bs4/doc/
- PostgreSQL full-text search: https://www.postgresql.org/docs/current/textsearch.html
- pgvector usage: https://github.com/pgvector/pgvector

---

## 14. License & Attribution

This template is part of the persistent-ai-memory ecosystem.

**License**: MIT

**Attribution**: When publishing or sharing derivatives:
- Credit: "Based on persistent-ai-memory Legal Hub template"
- Link: https://github.com/[your-repo]/persistent-ai-memory

---

**You're done!** You now have a complete Legal Hub system with:
- Multi-source legal data ingestion
- Pheromone-based quality learning
- MCP tools for legal research
- RLM integration for instant precedent access

For questions or improvements, contribute to the main repository.
