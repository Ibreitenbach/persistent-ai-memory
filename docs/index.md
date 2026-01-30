---
layout: default
title: Home
---

<div align="center">

# Legal Claw RLMemory

### Persistent AI Memory for Justice & Liberty

**FREE Forever** | **Battle-Tested** | **4,994+ Conversations**

---

<a href="START_HERE" style="display: inline-block; padding: 20px 40px; font-size: 24px; font-weight: bold; color: white; background: linear-gradient(135deg, #DC143C 0%, #1E3A8A 100%); border-radius: 12px; text-decoration: none; margin: 20px 0; box-shadow: 0 4px 15px rgba(0,0,0,0.3);">
START HERE
</a>

<p style="font-size: 14px; color: #666;">New? Click above for step-by-step setup instructions</p>

---

</div>

## What Is This?

Legal Claw RLMemory is a complete system for AI conversational memory that:

- **Loads filtered history once** at session start
- **Answers queries with 0ms retrieval latency**
- Uses **pheromone learning** to prioritize useful memories
- Provides **FREE access to legal information** for **ALL legal research**

## For Everyone With Legal Questions

This tool is designed for **anyone** seeking legal information - not just immigration:

| Legal Area | Example Use Cases |
|------------|-------------------|
| **Immigration** | Visa applications, green cards, citizenship, asylum |
| **Family Law** | Divorce, custody, adoption, guardianship |
| **Criminal Defense** | Understanding charges, rights during arrest, bail |
| **Housing & Tenant** | Evictions, lease disputes, landlord issues |
| **Employment** | Wrongful termination, discrimination, wage theft |
| **Small Claims** | Disputes under $10,000, contract issues |
| **Consumer Rights** | Debt collection, fraud, warranty claims |
| **Estate Planning** | Wills, trusts, probate basics |
| **Civil Rights** | Discrimination, police misconduct, voting rights |

**Remember:** This provides legal **information**, not legal **advice**. Always consult a licensed attorney for your specific situation.

## Quick Links

| Getting Started | Technical Docs | Resources |
|-----------------|----------------|-----------|
| [**Start Here**](START_HERE) | [Architecture](ARCHITECTURE) | [GitHub Repo](https://github.com/Ibreitenbach/Legal-Claw-RLMemory) |
| [Requirements](#requirements) | [RLM White Paper](RLM_WHITEPAPER) | [Legal Research Examples](https://github.com/Ibreitenbach/Legal-Claw-RLMemory/tree/main/examples/legal-research) |
| [FAQ](#faq) | [Membox Setup](MEMBOX_SETUP) | [Contributing](https://github.com/Ibreitenbach/Legal-Claw-RLMemory/blob/main/CONTRIBUTING.md) |
| | [DB Management](DATABASE_MANAGEMENT_TOOLS) | [Mission Statement](https://github.com/Ibreitenbach/Legal-Claw-RLMemory/blob/main/MISSION.md) |

## Requirements

Before starting, ensure you have:

- **Operating System**: Linux, macOS, or Windows (WSL2)
- **PostgreSQL 14+** with pgvector extension
- **Python 3.9+** with pip
- **Claude Code CLI** (Anthropic's CLI tool)
- **~50K tokens** of available context window
- **~200MB** disk space for the database

## Why Preload > RAG?

| Metric | RLM+Mempheromone | Traditional RAG |
|--------|------------------|-----------------|
| Query Latency | **0ms** | 150-1,440ms |
| 10-Query Conv. | **0ms total** | 1.5-14 seconds |
| Context Quality | Full history | Top-K fragments |
| Retrieval Failures | **0** | Possible |
| Cost per Query | **$0** | $0.05-0.10 |

## FAQ

**Q: Do I need to pay for anything?**
A: No. This is FREE forever. The only costs are your own compute and API usage.

**Q: Can I use this without Claude Code?**
A: The RLM plugin is designed for Claude Code, but the database schema and concepts work with any AI system.

**Q: How much data can it handle?**
A: Production-tested with 4,994+ conversations and ~50K tokens per session load.

**Q: Is my data private?**
A: Yes. Everything runs locally on your machine. No cloud uploads.

---

<div align="center">

**Built for America, By Americans, For All Americans**

*"Give me your tired, your poor, your huddled masses yearning to breathe free."*

[View on GitHub](https://github.com/Ibreitenbach/Legal-Claw-RLMemory) | [Report Issues](https://github.com/Ibreitenbach/Legal-Claw-RLMemory/issues)

</div>
