---
layout: default
title: Start Here
---

<h1 align="center">START HERE</h1>
<h3 align="center">Your Free AI Legal Research Assistant</h3>

<p align="center"><em>For ALL legal questions - immigration, family law, housing, employment, criminal defense, and more.<br/>Never set up programming tools before? No problem. These guides walk you through every step.</em></p>

---

## Choose Your Operating System

<div align="center" style="margin: 40px 0;">

<table>
<tr>
<td align="center" style="padding: 20px;">

### Windows

<a href="START-HERE-WINDOWS">
<img src="https://img.shields.io/badge/🪟_START--HERE-WINDOWS-0078D6?style=for-the-badge&logoColor=white" alt="Windows"/>
</a>

Windows 10 or 11<br/>
Uses WSL2 (Linux inside Windows)

</td>
<td align="center" style="padding: 20px;">

### Linux

<a href="START-HERE-LINUX">
<img src="https://img.shields.io/badge/🐧_START--HERE-LINUX-FCC624?style=for-the-badge&logoColor=black" alt="Linux"/>
</a>

Ubuntu, Debian, Fedora,<br/>
Arch, and others

</td>
<td align="center" style="padding: 20px;">

### macOS

<a href="START-HERE-MACOS">
<img src="https://img.shields.io/badge/🍎_START--HERE-macOS-000000?style=for-the-badge&logoColor=white" alt="macOS"/>
</a>

Monterey, Ventura, Sonoma<br/>
Intel or Apple Silicon (M1/M2/M3)

</td>
</tr>
</table>

</div>

---

## What Will Be Installed?

Each guide walks you through installing:

| Software | What It Does | Why You Need It |
|----------|--------------|-----------------|
| **PostgreSQL** | Database | Stores your AI's memories |
| **pgvector** | Database extension | Enables semantic search |
| **Python 3** | Programming language | Runs the memory system |
| **Git** | Version control | Downloads the code |
| **Node.js** | JavaScript runtime | Required for Claude Code |
| **Claude Code** | AI assistant | The AI that uses the memory |

**Total disk space needed:** ~1-2GB (varies by OS)

---

## What You'll Learn

By the end of these guides, you will have:

1. **Installed all prerequisites** - Every tool you need
2. **Set up PostgreSQL database** - Where memories are stored
3. **Installed Claude Code** - Anthropic's AI assistant
4. **Configured the RLM plugin** - Connects Claude to your memories
5. **Verified everything works** - Make sure it's all running

---

## How Long Will This Take?

| Operating System | Time Estimate | Notes |
|------------------|---------------|-------|
| **Windows** | 30-45 minutes | WSL2 installation takes longest |
| **Linux** | 15-25 minutes | Quickest setup |
| **macOS** | 20-30 minutes | Homebrew installation takes time |

*Times assume decent internet connection*

---

## Requirements Before You Start

**All systems need:**
- Internet connection
- Admin/sudo password
- At least 2GB free disk space
- At least 4GB RAM (8GB recommended)

**Windows specific:**
- Windows 10 version 2004+ or Windows 11
- Hardware virtualization enabled in BIOS

**macOS specific:**
- macOS 12 (Monterey) or newer

---

## Frequently Asked Questions

**Q: I've never used command line/terminal before. Is this too hard?**

A: No! The guides are written for complete beginners. You'll copy and paste commands - no programming knowledge required.

**Q: Is this free?**

A: Yes, completely free. All the software is open source or free to use.

**Q: What about Claude Code - is that free too?**

A: Claude Code requires an Anthropic API key. See [anthropic.com](https://anthropic.com) for pricing. The memory system itself is free.

**Q: Can I stop partway and continue later?**

A: Yes! Each step is self-contained. Just note where you stopped.

**Q: What if something goes wrong?**

A: Each guide has a Troubleshooting section. You can also [open a GitHub issue](https://github.com/Ibreitenbach/Legal-Claw-RLMemory/issues).

---

## Ready to Start?

<div align="center" style="margin: 30px 0;">

| [🪟 Windows](START-HERE-WINDOWS) | [🐧 Linux](START-HERE-LINUX) | [🍎 macOS](START-HERE-MACOS) |
|:---:|:---:|:---:|

</div>

---

## Already Installed? Quick Commands

If you've already completed setup, here are the key commands:

```bash
# Start Claude Code with memory
cd ~/Legal-Claw-RLMemory
claude

# Check if PostgreSQL is running
psql -d mempheromone -c "SELECT COUNT(*) FROM debugging_facts;"

# Verify plugin is installed
ls ~/.claude/plugins/rlm-mempheromone/
```

---

<div align="center">

[Back to Home](index) | [View Architecture Docs](ARCHITECTURE) | [Immigration Guide](https://github.com/Ibreitenbach/Legal-Claw-RLMemory/blob/main/examples/legal-research/IMMIGRATION_LAW_GUIDE.md)

</div>
