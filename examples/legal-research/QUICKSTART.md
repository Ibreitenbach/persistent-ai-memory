# Legal Hub - Quick Start Guide

**Get your Legal Hub running in 15 minutes!**

[🇪🇸 Versión en Español](INICIO_RAPIDO.md)

---

## What You'll Get

A complete legal research assistant with:
- ✅ Federal court case search (CourtListener)
- ✅ State court cases (your jurisdiction)
- ✅ Citation tracking and precedent analysis
- ✅ Persistent memory with pheromone learning
- ✅ Instant search (0ms after session load)

---

## Prerequisites

Before you start, make sure you have:

- [ ] **PostgreSQL 14+** installed
  ```bash
  # Check version
  psql --version
  ```

- [ ] **Python 3.9+** installed
  ```bash
  # Check version
  python3 --version
  ```

- [ ] **Git** installed
  ```bash
  # Check version
  git --version
  ```

- [ ] **Claude Code CLI** (optional, for RLM integration)
  ```bash
  # Check if installed
  which claude
  ```

---

## Step 1: Clone Repository

```bash
# Clone the repository
git clone https://github.com/Ibreitenbach/Legal-Claw-RLMemory
cd Legal-Claw-RLMemory/examples/legal-research

# Make setup script executable
chmod +x setup.sh
```

**What this does:** Downloads all the code you need.

---

## Step 2: Run Automated Setup

```bash
# Run the setup script
./setup.sh

# This will:
# 1. Create PostgreSQL database
# 2. Install required Python packages
# 3. Set up database tables
# 4. Ask for your CourtListener API key
```

**What you'll need:**
- CourtListener API key (free - we'll get this in Step 3)

**Time:** ~5 minutes

---

## Step 3: Get CourtListener API Key (FREE)

CourtListener provides **free** access to federal and state court opinions.

### 3.1. Create Account

1. Go to: https://www.courtlistener.com/
2. Click **"Sign Up"** (top right)
3. Create free account with your email

### 3.2. Get API Token

1. After login, click your username (top right)
2. Select **"Profile"**
3. Click **"API"** tab
4. Click **"Generate New API Token"**
5. **Copy the token** (looks like: `a1b2c3d4e5f6...`)

### 3.3. Save API Token

```bash
# Save your API token
export COURTLISTENER_API_TOKEN="your_token_here"

# Make it permanent (add to your .bashrc or .zshrc)
echo 'export COURTLISTENER_API_TOKEN="your_token_here"' >> ~/.bashrc
```

**Important:** Replace `your_token_here` with your actual token!

---

## Step 4: Test Your Setup

```bash
# Test database connection
psql -d legal_hub -c "SELECT COUNT(*) FROM legal_cases;"
# Should show: 0 (no cases yet - that's correct!)

# Test CourtListener API
python3 scripts/test_courtlistener.py
# Should show: ✅ Connection successful
```

**If you see errors:**
- Check your API token is set correctly
- Make sure PostgreSQL is running: `sudo systemctl status postgresql`

---

## Step 5: Import Your First Cases

Let's import some Supreme Court cases about constitutional rights:

```bash
# Import 25 Supreme Court cases
python3 scripts/ingest_courtlistener.py \
    "constitutional rights" \
    --court scotus \
    --limit 25

# This will:
# - Search CourtListener
# - Download case details
# - Store in your database
# - Generate embeddings for search

# Takes about 2-3 minutes
```

**What you'll see:**
```
🔍 Searching CourtListener: constitutional rights
📊 Found 25 opinions
  ✓ Stored: Roe v. Wade (410 U.S. 113)
  ✓ Stored: Brown v. Board of Education (347 U.S. 483)
  ✓ Stored: Miranda v. Arizona (384 U.S. 436)
  ...
✅ Ingestion Complete
   Stored: 25 new cases
```

---

## Step 6: Search Your Cases

Now you can search your legal database:

```bash
# Search for cases about search and seizure
python3 scripts/search_cases.py "Fourth Amendment search seizure"

# Search for cases in a specific jurisdiction
python3 scripts/search_cases.py "due process" --jurisdiction federal

# Find precedents for a legal issue
python3 scripts/search_cases.py "unreasonable search" --min-pheromone 10
```

**Example output:**
```
Found 8 cases:

1. Mapp v. Ohio
   Citation: 367 U.S. 643
   Court: Supreme Court of the United States
   Decided: 1961-06-19
   Pheromone: 10.0
   Summary: The exclusionary rule applies to states...
   URL: https://www.courtlistener.com/...

2. Terry v. Ohio
   Citation: 392 U.S. 1
   ...
```

---

## Step 7: Add Your State/Local Courts (Optional)

### 7.1. Find Your State Court System

**Google search pattern:**
```
"[Your State] court records online"
"[Your State] judicial system case search"
```

**Example for Oklahoma:**
1. Search: "Oklahoma court records online"
2. Find: https://www.oscn.net/ (Oklahoma State Courts Network)
3. No API key needed - public records!

### 7.2. Customize Scraper

```bash
# Copy the template scraper
cp scripts/ingest_state_courts_template.py scripts/ingest_oklahoma.py

# Edit for your state
nano scripts/ingest_oklahoma.py

# Customize the scrape_state_case() function
# (We provide examples for Oklahoma, see the code)
```

### 7.3. Import State Cases

```bash
# Import a case from your state court
python3 scripts/ingest_oklahoma.py CF-2020-123 --county Oklahoma

# Import multiple cases
python3 scripts/ingest_oklahoma.py CF-2020-123 CF-2020-456 CF-2021-789
```

---

## Step 8: Set Up Claude Code Integration (Optional)

If you use Claude Code, integrate Legal Hub for instant access:

```bash
# Copy plugin configuration
cp claude_plugin/legal_hub_plugin.json ~/.claude/plugins/

# Edit configuration
nano ~/.claude/plugins/legal_hub_plugin.json

# Update database connection string:
# "POSTGRES_CONNECTION_STRING": "postgresql://yourusername@/legal_hub?host=/var/run/postgresql"
```

**Now when you start Claude Code:**
- Your legal cases are automatically loaded
- Search with 0ms latency
- Pheromone scores improve as you use cases

---

## Step 9: Explore Advanced Features

### 9.1. Citation Tracking

```bash
# Find all cases citing a specific case
python3 scripts/track_citations.py "410 U.S. 113"  # Roe v. Wade

# See what cases a decision relies on
python3 scripts/track_citations.py "410 U.S. 113" --direction cited
```

### 9.2. Precedent Analysis

```bash
# Find precedents for a legal issue
python3 scripts/analyze_precedents.py "privacy rights abortion"

# Filter by jurisdiction and quality
python3 scripts/analyze_precedents.py \
    "equal protection" \
    --jurisdiction federal \
    --min-pheromone 12
```

### 9.3. Batch Import

```bash
# Import 100 cases on a topic
python3 scripts/ingest_courtlistener.py \
    "contract law" \
    --limit 100 \
    --jurisdiction ca  # California

# Import from multiple courts
python3 scripts/batch_import.py topics.txt
# (topics.txt contains one topic per line)
```

---

## Troubleshooting

### Problem: "psql: command not found"

**Solution:** PostgreSQL not installed
```bash
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# macOS
brew install postgresql
```

### Problem: "API 401: Unauthorized"

**Solution:** API token not set or invalid
```bash
# Check if token is set
echo $COURTLISTENER_API_TOKEN

# If empty, set it again
export COURTLISTENER_API_TOKEN="your_token_here"

# Test the token
curl -H "Authorization: Token $COURTLISTENER_API_TOKEN" \
  "https://www.courtlistener.com/api/rest/v3/search/?q=test&type=o"
```

### Problem: "Database 'legal_hub' does not exist"

**Solution:** Run setup script again
```bash
./setup.sh
```

### Problem: "No cases found"

**Solution:** Check your search query
```bash
# Try a broader search
python3 scripts/search_cases.py "rights"

# Check how many cases are in database
psql -d legal_hub -c "SELECT COUNT(*) FROM legal_cases;"
```

### Problem: State court scraper not working

**Solution:** State court websites change frequently
1. Visit your state court website
2. Open browser developer tools (F12)
3. Inspect the HTML structure
4. Update the scraper to match current structure
5. See `scripts/ingest_state_courts_template.py` for examples

---

## Next Steps

**Now that you're set up:**

1. **Import more cases** on topics relevant to your work
2. **Set up automatic imports** (cron job) for new cases
3. **Customize for your practice area** (add specialized tables)
4. **Integrate with Claude Code** for AI-powered research
5. **Build citation graphs** to understand precedent networks

---

## Resources

### Documentation
- [Full Legal Hub Guide](../../.ai/BUILD_LEGAL_HUB.md) - Complete technical docs
- [Database Schema](schema_extensions.sql) - Legal-specific tables
- [API Reference](API.md) - All available functions

### Data Sources
- **CourtListener**: https://www.courtlistener.com/
- **Free Law Project**: https://free.law/
- **Justia**: https://www.justia.com/
- **Google Scholar (Legal)**: https://scholar.google.com/ (select "Case law")

### State Court Directories
- **NCSC State Court Links**: https://www.ncsc.org/information-and-resources/state-court-websites
- Find your state court system and check for online records

---

## Support

**Need help?**

1. Check troubleshooting section above
2. See full documentation: [BUILD_LEGAL_HUB.md](../../.ai/BUILD_LEGAL_HUB.md)
3. Open an issue on GitHub: https://github.com/Ibreitenbach/Legal-Claw-RLMemory/issues

---

## Success Checklist

After completing this guide, you should have:

- [x] PostgreSQL database created
- [x] CourtListener API token configured
- [x] 25+ Supreme Court cases imported
- [x] Able to search cases
- [x] Understanding how to add state/local courts
- [x] (Optional) Claude Code integration working

**Congratulations! Your Legal Hub is ready!** 🎉

---

**Next:** [Spanish Version →](INICIO_RAPIDO.md)
