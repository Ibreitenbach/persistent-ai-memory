# Persistent AI Memory: RLM + Mempheromone

Give your AI persistent memory that loads once per session and queries instantly.

[🇪🇸 Versión en Español](README_ES.md)

---

## 🌎 Built for All Americans - FREE Forever

**We are a nation of immigrants.** From every corner of the world, people have come to America bringing their cultures, languages, and dreams. This project celebrates that heritage.

### 💡 [Read Our Mission Statement](MISSION.md)

**Why this tool is FREE and why it matters NOW:**
- During times of ICE enforcement, knowledge is power
- Legal information should not be a privilege for the wealthy
- Understanding your rights protects families
- Legal immigration pathways exist - we make them clear
- Access to justice is a fundamental right

**This tool provides:**
- ✅ FREE access to federal immigration case law
- ✅ Know Your Rights information
- ✅ Legal pathways clearly explained
- ✅ Connection to pro bono legal services
- ✅ Zero cost forever - no paywalls, no barriers

Whether your family came on the Mayflower, through Ellis Island, across the Rio Grande, from Asia, Africa, Europe, or the Americas—**you belong here.** This technology is built **by** immigrants, **for** immigrants, and for **all Americans** who believe in the strength of our diversity.

**We welcome contributors** from every background:
- 🇲🇽 🇨🇳 🇮🇳 🇵🇭 🇻🇳 🇰🇷 🇯🇵 🇹🇭 Asian & Pacific Islander Americans
- 🇲🇽 🇨🇺 🇵🇷 🇨🇴 🇩🇴 🇸🇻 🇬🇹 🇭🇳 Latino & Hispanic Americans
- 🇳🇬 🇪🇹 🇰🇪 🇬🇭 🇿🇦 African & Black Americans
- 🇮🇹 🇵🇱 🇩🇪 🇮🇪 🇬🇷 🇫🇷 European Americans
- 🏳️‍🌈 LGBTQ+ Americans
- ✊🏽 Indigenous & Native Americans
- 🕊️ Muslim, Jewish, Christian, Hindu, Buddhist, Sikh, and all faith traditions

**America's greatest strength is our diversity.** This project is open-source, bilingual (English/Spanish, with more languages welcome), and committed to making AI technology accessible to **everyone**.

*"Give me your tired, your poor, your huddled masses yearning to breathe free."* — Emma Lazarus

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to get involved.

---

## What Is This?

A complete system for AI conversational memory that:
- ✅ Loads filtered history **once** at session start
- ✅ Answers queries with **0ms retrieval latency**
- ✅ Uses **pheromone learning** to prioritize useful memories
- ✅ **Battle-tested** with 4,994+ real conversations

## Why Preload > RAG?

**Traditional RAG Systems** (Mem0, MemGPT):
- Retrieve on EVERY query → 150-1,440ms latency
- Partial context → missed connections
- Cumulative cost → $0.01-0.10 per query

**Preload Architecture** (RLM + Mempheromone):
- Load once per session → 0ms query latency
- Full filtered context → complete understanding
- Zero marginal cost → unlimited queries

**For a 10-query conversation:**
- RAG: 1.5-14 seconds of retrieval time
- Preload: 0 seconds (already in context!)

## Quick Start

```bash
# 1. Clone repository
git clone https://github.com/Ibreitenbach/Legal-Claw-RLMemory
cd Legal-Claw-RLMemory

# 2. Setup database
./scripts/setup.sh

# 3. Install RLM plugin
cp -r rlm-plugin ~/.claude/plugins/rlm-mempheromone

# 4. Start using - memory automatically loads!
```

## Production Results

**Real Usage** (4,994 conversations):
- Session load: 1.5 MB (27,036 lines)
- Context size: ~50K tokens (fits in 200K window)
- Query latency: 0ms (already in context)
- Retrieval failures: 0 (impossible - it's all there!)

**Benchmarks** (50 queries):
- Hybrid RRF: P@5 = 0.144 (+80% improvement)
- Average latency: 21ms
- Cost: $0 (self-hosted)

**Membox** (Topic-Continuous Memory):
- 755 memory boxes with trace links
- Automatic background processing
- Pheromone-based quality learning

## Components

### 1. RLM Plugin (Session Awakening)
- Triggers on session start
- Loads high-quality memories (pheromone >= 10)
- Exports ~50K tokens to context
- Zero query latency after load

### 2. Mempheromone Database
- PostgreSQL + pgvector
- Pheromone scores (RL-trained quality signals)
- Topic-continuous memory boxes (membox)
- Citation graphs and trace links

### 3. Membox (Topic-Continuous Memory)
- Groups related memories by topic
- Links across topic boundaries via events
- Navigable memory structure
- Automatic background processing

### 4. Database Management Tools
- Health monitoring and statistics
- Quality analysis and cleanup
- Embedding regeneration
- Performance optimization

## Documentation

### For Everyone
- **[Mission Statement](MISSION.md)** - Why this is FREE and why it matters
- **[Immigration Law Guide](examples/legal-research/IMMIGRATION_LAW_GUIDE.md)** - Using Legal Hub for immigration research
- [Contributing Guide](CONTRIBUTING.md) - How to help (all backgrounds welcome!)

### Technical Documentation
- [Architecture Deep Dive](docs/ARCHITECTURE.md) - Complete technical architecture
- [RLM White Paper](docs/RLM_WHITEPAPER.md) - Complete technical docs
- [Membox Setup Guide](docs/MEMBOX_SETUP.md) - Integration guide
- [Database Management](docs/DATABASE_MANAGEMENT_TOOLS.md) - DB tools reference
- [Legal Hub Build Guide](.ai/BUILD_LEGAL_HUB.md) - Domain-specific variant

## AI-Buildable

**Special Feature**: `.ai/` directory contains AI-readable handoff documents.
AI agents like Claude Code can build entire system from instructions autonomously.

## Performance Comparison

| Metric | RLM+Mempheromone | Mem0 | MemGPT |
|--------|------------------|------|---------|
| Query Latency | **0ms** | 1,440ms | 150ms |
| 10-Query Conv. | **0ms** | 14,400ms | 1,500ms |
| Context Quality | Full history | Top-K | Top-K |
| Retrieval Failures | **0** | Possible | Possible |
| Cost per Query | **$0** | $0.10 | $0.05 |

## When To Use This

**Use Preload When:**
- ✅ Session-based conversations
- ✅ Need full context understanding
- ✅ Want zero retrieval latency
- ✅ Context fits in window (~50K tokens)
- ✅ Self-hosted deployment

**Use RAG When:**
- ⚠️ One-off queries (no session)
- ⚠️ Context too large for window (>100K tokens)
- ⚠️ Dynamic corpus (changes during session)

## Requirements

- PostgreSQL 14+ with pgvector extension
- Python 3.9+
- Claude Code CLI (for RLM plugin)
- ~50K tokens of available context window

## License

MIT License - see LICENSE file

## Contributing

Contributions welcome! This is a production-tested system with real-world usage.

---

**Built by Ike Breitenbach**
**Production-tested with 4,994+ conversations**
**Battle-hardened in daily multi-agent use**
