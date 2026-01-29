# Database Management MCP Tools

**Purpose**: Essential database management and monitoring tools for mempheromone system.

**Location**: These tools should be included in the core MCP server (`mcp-server/src/tools/db_management/`)

---

## Tool Catalog

### 1. Database Statistics

**Tool**: `get_database_stats`

**Purpose**: Get overview of database health and size

**Implementation**:

```typescript
import { z } from 'zod';
import { Pool } from 'pg';

const GetDatabaseStatsSchema = z.object({
  include_details: z.boolean().default(false).describe('Include detailed table stats')
});

export async function get_database_stats(
  args: z.infer<typeof GetDatabaseStatsSchema>,
  pool: Pool
): Promise<string> {
  const { include_details } = args;

  // Overall stats
  const statsQuery = `
    SELECT
      (SELECT COUNT(*) FROM debugging_facts) as debugging_facts,
      (SELECT COUNT(*) FROM claude_memories) as claude_memories,
      (SELECT COUNT(*) FROM crystallization_events) as crystallizations,
      (SELECT COUNT(*) FROM session_narratives) as narratives,
      (SELECT COUNT(*) FROM wisdom) as wisdom_entries,
      (SELECT COUNT(*) FROM embeddings) as embeddings,
      (SELECT COUNT(*) FROM memory_boxes) as memory_boxes,
      (SELECT COUNT(*) FROM trace_links) as trace_links,
      (SELECT AVG(pheromone_score) FROM debugging_facts) as avg_pheromone,
      (SELECT COUNT(*) FROM debugging_facts WHERE pheromone_score >= 15) as expert_facts,
      (SELECT COUNT(*) FROM debugging_facts WHERE pheromone_score >= 10) as solid_facts,
      (SELECT pg_database_size(current_database())) as db_size_bytes
  `;

  const result = await pool.query(statsQuery);
  const stats = result.rows[0];

  let output = `📊 Mempheromone Database Statistics\n\n`;
  output += `Memory Counts:\n`;
  output += `  Debugging Facts: ${stats.debugging_facts}\n`;
  output += `  Claude Memories: ${stats.claude_memories}\n`;
  output += `  Crystallizations: ${stats.crystallizations}\n`;
  output += `  Session Narratives: ${stats.narratives}\n`;
  output += `  Wisdom Entries: ${stats.wisdom_entries}\n`;
  output += `  Embeddings: ${stats.embeddings}\n`;
  output += `  Memory Boxes: ${stats.memory_boxes}\n`;
  output += `  Trace Links: ${stats.trace_links}\n\n`;

  output += `Quality Metrics:\n`;
  output += `  Average Pheromone: ${parseFloat(stats.avg_pheromone).toFixed(2)}\n`;
  output += `  Expert Facts (≥15): ${stats.expert_facts}\n`;
  output += `  Solid Facts (≥10): ${stats.solid_facts}\n\n`;

  const dbSizeMB = (parseInt(stats.db_size_bytes) / 1024 / 1024).toFixed(2);
  output += `Database Size: ${dbSizeMB} MB\n`;

  if (include_details) {
    // Table sizes
    const tableSizeQuery = `
      SELECT
        schemaname,
        tablename,
        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
      FROM pg_tables
      WHERE schemaname = 'public'
      ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
      LIMIT 10
    `;

    const tableSizes = await pool.query(tableSizeQuery);

    output += `\nTop 10 Tables by Size:\n`;
    for (const row of tableSizes.rows) {
      output += `  ${row.tablename}: ${row.size}\n`;
    }
  }

  return output;
}

export const get_database_stats_tool = {
  name: 'get_database_stats',
  description: 'Get overview of mempheromone database health, memory counts, and quality metrics',
  inputSchema: GetDatabaseStatsSchema
};
```

---

### 2. Pheromone Distribution Analysis

**Tool**: `get_pheromone_distribution`

**Purpose**: Analyze pheromone score distribution to understand memory quality

**Implementation**:

```typescript
const GetPheromoneDistributionSchema = z.object({
  memory_type: z.enum(['debugging_facts', 'memory_boxes', 'all']).default('all')
});

export async function get_pheromone_distribution(
  args: z.infer<typeof GetPheromoneDistributionSchema>,
  pool: Pool
): Promise<string> {
  const { memory_type } = args;

  let output = `📈 Pheromone Score Distribution\n\n`;

  if (memory_type === 'debugging_facts' || memory_type === 'all') {
    const debuggingQuery = `
      SELECT
        CASE
          WHEN pheromone_score >= 20 THEN 'Expert+ (20)'
          WHEN pheromone_score >= 15 THEN 'Expert (15-19)'
          WHEN pheromone_score >= 12 THEN 'Solid+ (12-14)'
          WHEN pheromone_score >= 10 THEN 'Solid (10-11)'
          WHEN pheromone_score >= 5 THEN 'Unproven (5-9)'
          ELSE 'Low (<5)'
        END as tier,
        COUNT(*) as count,
        AVG(pheromone_score) as avg_score,
        MIN(pheromone_score) as min_score,
        MAX(pheromone_score) as max_score
      FROM debugging_facts
      GROUP BY tier
      ORDER BY MIN(pheromone_score) DESC
    `;

    const result = await pool.query(debuggingQuery);

    output += `Debugging Facts:\n`;
    for (const row of result.rows) {
      const pct = (row.count / result.rows.reduce((sum, r) => sum + parseInt(r.count), 0) * 100).toFixed(1);
      output += `  ${row.tier}: ${row.count} (${pct}%) - avg: ${parseFloat(row.avg_score).toFixed(2)}\n`;
    }
    output += '\n';
  }

  if (memory_type === 'memory_boxes' || memory_type === 'all') {
    const boxesQuery = `
      SELECT
        CASE
          WHEN pheromone_score >= 20 THEN 'Expert+ (20)'
          WHEN pheromone_score >= 15 THEN 'Expert (15-19)'
          WHEN pheromone_score >= 12 THEN 'Solid+ (12-14)'
          WHEN pheromone_score >= 10 THEN 'Solid (10-11)'
          WHEN pheromone_score >= 5 THEN 'Unproven (5-9)'
          ELSE 'Low (<5)'
        END as tier,
        COUNT(*) as count,
        AVG(pheromone_score) as avg_score,
        AVG(memory_count) as avg_memories_per_box
      FROM memory_boxes
      WHERE is_active = TRUE
      GROUP BY tier
      ORDER BY MIN(pheromone_score) DESC
    `;

    const result = await pool.query(boxesQuery);

    output += `Memory Boxes:\n`;
    for (const row of result.rows) {
      output += `  ${row.tier}: ${row.count} boxes - avg: ${parseFloat(row.avg_score).toFixed(2)} - avg memories/box: ${parseFloat(row.avg_memories_per_box).toFixed(1)}\n`;
    }
  }

  return output;
}

export const get_pheromone_distribution_tool = {
  name: 'get_pheromone_distribution',
  description: 'Analyze pheromone score distribution across memory types',
  inputSchema: GetPheromoneDistributionSchema
};
```

---

### 3. Memory Quality Analysis

**Tool**: `analyze_memory_quality`

**Purpose**: Identify quality issues and suggest improvements

**Implementation**:

```typescript
export async function analyze_memory_quality(pool: Pool): Promise<string> {
  let output = `🔍 Memory Quality Analysis\n\n`;

  // 1. Stale memories (not accessed recently)
  const staleQuery = `
    SELECT COUNT(*) as stale_count
    FROM debugging_facts
    WHERE last_accessed < NOW() - INTERVAL '90 days'
      AND pheromone_score < 10
  `;
  const stale = await pool.query(staleQuery);
  output += `Stale Memories (>90 days, low pheromone): ${stale.rows[0].stale_count}\n`;

  // 2. Missing embeddings
  const missingEmbeddingsQuery = `
    SELECT COUNT(*) as missing
    FROM debugging_facts df
    LEFT JOIN embeddings e ON df.fact_id = e.memory_id
    WHERE e.memory_id IS NULL
  `;
  const missing = await pool.query(missingEmbeddingsQuery);
  output += `Missing Embeddings: ${missing.rows[0].missing}\n`;

  // 3. Never accessed memories
  const neverAccessedQuery = `
    SELECT COUNT(*) as never_accessed
    FROM debugging_facts
    WHERE search_count = 0 OR search_count IS NULL
  `;
  const neverAccessed = await pool.query(neverAccessedQuery);
  output += `Never Accessed: ${neverAccessed.rows[0].never_accessed}\n`;

  // 4. High-pheromone but never retrieved
  const highButUnusedQuery = `
    SELECT COUNT(*) as count
    FROM debugging_facts
    WHERE pheromone_score >= 12
      AND (retrieval_count = 0 OR retrieval_count IS NULL)
  `;
  const highUnused = await pool.query(highButUnusedQuery);
  output += `High Pheromone but Never Retrieved: ${highUnused.rows[0].count}\n`;

  // 5. Membox coverage
  const memboxCoverageQuery = `
    SELECT
      COUNT(DISTINCT df.fact_id) as total_facts,
      COUNT(DISTINCT mbi.memory_id) as facts_in_boxes,
      (COUNT(DISTINCT mbi.memory_id)::float / COUNT(DISTINCT df.fact_id) * 100) as coverage_pct
    FROM debugging_facts df
    LEFT JOIN memory_box_items mbi ON df.fact_id = mbi.memory_id AND mbi.memory_type = 'debugging_fact'
  `;
  const coverage = await pool.query(memboxCoverageQuery);
  output += `\nMembox Coverage:\n`;
  output += `  Total Facts: ${coverage.rows[0].total_facts}\n`;
  output += `  In Boxes: ${coverage.rows[0].facts_in_boxes}\n`;
  output += `  Coverage: ${parseFloat(coverage.rows[0].coverage_pct).toFixed(1)}%\n`;

  // 6. Recommendations
  output += `\n💡 Recommendations:\n`;

  if (parseInt(stale.rows[0].stale_count) > 100) {
    output += `  ⚠️  Consider cleaning up ${stale.rows[0].stale_count} stale, low-quality memories\n`;
  }

  if (parseInt(missing.rows[0].missing) > 0) {
    output += `  ⚠️  Regenerate ${missing.rows[0].missing} missing embeddings\n`;
  }

  if (parseFloat(coverage.rows[0].coverage_pct) < 50) {
    output += `  ⚠️  Low membox coverage (${parseFloat(coverage.rows[0].coverage_pct).toFixed(1)}%) - consider running membox bootstrap\n`;
  }

  return output;
}

export const analyze_memory_quality_tool = {
  name: 'analyze_memory_quality',
  description: 'Identify quality issues and provide improvement recommendations',
  inputSchema: z.object({})
};
```

---

### 4. Cleanup Low-Quality Memories

**Tool**: `cleanup_low_quality_memories`

**Purpose**: Remove or archive memories below quality threshold

**Implementation**:

```typescript
const CleanupLowQualityMemoriesSchema = z.object({
  min_pheromone: z.number().default(3.0).describe('Delete memories below this score'),
  min_age_days: z.number().default(90).describe('Only delete memories older than this'),
  dry_run: z.boolean().default(true).describe('Preview deletions without actually deleting')
});

export async function cleanup_low_quality_memories(
  args: z.infer<typeof CleanupLowQualityMemoriesSchema>,
  pool: Pool
): Promise<string> {
  const { min_pheromone, min_age_days, dry_run } = args;

  // Find candidates for deletion
  const findQuery = `
    SELECT fact_id, symptom, pheromone_score, last_accessed, search_count
    FROM debugging_facts
    WHERE pheromone_score < $1
      AND last_accessed < NOW() - INTERVAL '${min_age_days} days'
      AND (search_count = 0 OR search_count IS NULL)
    ORDER BY pheromone_score ASC
    LIMIT 100
  `;

  const candidates = await pool.query(findQuery, [min_pheromone]);

  let output = `🧹 Cleanup Low-Quality Memories\n\n`;
  output += `Criteria:\n`;
  output += `  Pheromone < ${min_pheromone}\n`;
  output += `  Age > ${min_age_days} days\n`;
  output += `  Never searched\n\n`;

  output += `Found ${candidates.rows.length} candidates for deletion:\n\n`;

  if (candidates.rows.length === 0) {
    return output + `No memories match cleanup criteria. Database is clean! ✨\n`;
  }

  for (const row of candidates.rows.slice(0, 10)) {
    output += `  [ψ=${row.pheromone_score.toFixed(1)}] ${row.symptom.substring(0, 60)}...\n`;
  }

  if (candidates.rows.length > 10) {
    output += `  ... and ${candidates.rows.length - 10} more\n`;
  }

  if (dry_run) {
    output += `\n⚠️  DRY RUN - No deletions performed.\n`;
    output += `Set dry_run=false to actually delete these memories.\n`;
  } else {
    // Actually delete
    const deleteQuery = `
      DELETE FROM debugging_facts
      WHERE pheromone_score < $1
        AND last_accessed < NOW() - INTERVAL '${min_age_days} days'
        AND (search_count = 0 OR search_count IS NULL)
    `;

    const deleteResult = await pool.query(deleteQuery, [min_pheromone]);

    output += `\n✅ Deleted ${deleteResult.rowCount} low-quality memories.\n`;
  }

  return output;
}

export const cleanup_low_quality_memories_tool = {
  name: 'cleanup_low_quality_memories',
  description: 'Remove or archive memories below quality threshold (supports dry-run)',
  inputSchema: CleanupLowQualityMemoriesSchema
};
```

---

### 5. Rebuild Embeddings

**Tool**: `rebuild_embeddings`

**Purpose**: Regenerate embeddings for memories missing them

**Implementation**:

```typescript
const RebuildEmbeddingsSchema = z.object({
  memory_type: z.enum(['debugging_facts', 'claude_memories', 'all']).default('all'),
  limit: z.number().default(100).describe('Max embeddings to generate per run'),
  force: z.boolean().default(false).describe('Regenerate even if embedding exists')
});

export async function rebuild_embeddings(
  args: z.infer<typeof RebuildEmbeddingsSchema>,
  pool: Pool
): Promise<string> {
  const { memory_type, limit, force } = args;

  let output = `🔄 Rebuild Embeddings\n\n`;

  // Find memories missing embeddings
  let findQuery: string;

  if (memory_type === 'debugging_facts' || memory_type === 'all') {
    findQuery = `
      SELECT df.fact_id as memory_id, df.symptom || ': ' || df.solution as content
      FROM debugging_facts df
      LEFT JOIN embeddings e ON df.fact_id = e.memory_id
      WHERE ${force ? 'TRUE' : 'e.memory_id IS NULL'}
      LIMIT $1
    `;

    const missing = await pool.query(findQuery, [limit]);

    output += `Debugging Facts: ${missing.rows.length} embeddings to generate\n`;

    // Note: Actual embedding generation would require calling embedding service
    // This is a placeholder showing the structure
    output += `⚠️  Embedding generation requires external service (sentence-transformers)\n`;
    output += `   Use: python3 scripts/generate_embeddings.py --limit ${limit}\n`;
  }

  return output;
}

export const rebuild_embeddings_tool = {
  name: 'rebuild_embeddings',
  description: 'Regenerate embeddings for memories missing them',
  inputSchema: RebuildEmbeddingsSchema
};
```

---

### 6. Check Membox Status

**Tool**: `check_membox_status`

**Purpose**: Verify if membox system is working correctly

**Implementation**:

```typescript
export async function check_membox_status(pool: Pool): Promise<string> {
  let output = `📦 Membox System Status\n\n`;

  // 1. Check if tables exist
  const tablesQuery = `
    SELECT tablename
    FROM pg_tables
    WHERE schemaname = 'public'
      AND tablename IN ('memory_boxes', 'memory_box_items', 'trace_links')
    ORDER BY tablename
  `;

  const tables = await pool.query(tablesQuery);
  const tableNames = tables.rows.map(r => r.tablename);

  output += `Required Tables:\n`;
  output += `  memory_boxes: ${tableNames.includes('memory_boxes') ? '✅' : '❌ MISSING'}\n`;
  output += `  memory_box_items: ${tableNames.includes('memory_box_items') ? '✅' : '❌ MISSING'}\n`;
  output += `  trace_links: ${tableNames.includes('trace_links') ? '✅' : '❌ MISSING'}\n\n`;

  if (tableNames.length < 3) {
    output += `⚠️  Membox tables missing! Run schema migration:\n`;
    output += `   psql -d mempheromone -f schema/membox_tables.sql\n`;
    return output;
  }

  // 2. Check if boxes exist
  const boxCountQuery = `
    SELECT
      COUNT(*) as total_boxes,
      COUNT(*) FILTER (WHERE is_active = TRUE) as active_boxes,
      AVG(memory_count) as avg_memories_per_box,
      MAX(memory_count) as max_memories_in_box,
      AVG(pheromone_score) as avg_pheromone
    FROM memory_boxes
  `;

  const boxStats = await pool.query(boxCountQuery);
  const stats = boxStats.rows[0];

  output += `Memory Boxes:\n`;
  output += `  Total: ${stats.total_boxes}\n`;
  output += `  Active: ${stats.active_boxes}\n`;
  output += `  Avg Memories/Box: ${parseFloat(stats.avg_memories_per_box || 0).toFixed(1)}\n`;
  output += `  Max Memories in Box: ${stats.max_memories_in_box || 0}\n`;
  output += `  Avg Pheromone: ${parseFloat(stats.avg_pheromone || 0).toFixed(2)}\n\n`;

  if (parseInt(stats.total_boxes) === 0) {
    output += `⚠️  No memory boxes exist! Membox system not bootstrapped.\n`;
    output += `   Run: python3 scripts/mempheromone_membox.py bootstrap\n\n`;
  }

  // 3. Check trace links
  const linksQuery = `
    SELECT COUNT(*) as total_links
    FROM trace_links
  `;

  const links = await pool.query(linksQuery);
  output += `Trace Links: ${links.rows[0].total_links}\n\n`;

  if (parseInt(links.rows[0].total_links) === 0 && parseInt(stats.total_boxes) > 0) {
    output += `⚠️  No trace links exist but boxes do. Trace weaver may not be running.\n\n`;
  }

  // 4. Recent activity
  const recentActivityQuery = `
    SELECT
      MAX(created_at) as last_box_created,
      MAX(updated_at) as last_box_updated
    FROM memory_boxes
  `;

  const activity = await pool.query(recentActivityQuery);

  if (activity.rows[0].last_box_created) {
    const lastCreated = new Date(activity.rows[0].last_box_created);
    const lastUpdated = new Date(activity.rows[0].last_box_updated);
    const daysSinceCreated = Math.floor((Date.now() - lastCreated.getTime()) / (1000 * 60 * 60 * 24));
    const daysSinceUpdated = Math.floor((Date.now() - lastUpdated.getTime()) / (1000 * 60 * 60 * 24));

    output += `Recent Activity:\n`;
    output += `  Last Box Created: ${daysSinceCreated} days ago\n`;
    output += `  Last Box Updated: ${daysSinceUpdated} days ago\n\n`;

    if (daysSinceUpdated > 7) {
      output += `⚠️  No recent updates to boxes (${daysSinceUpdated} days). Membox may not be integrated into workflow.\n`;
      output += `   Check if membox is called when new memories are stored.\n\n`;
    } else {
      output += `✅ Membox system is actively being used!\n\n`;
    }
  }

  // 5. Overall status
  const isWorking =
    tableNames.length === 3 &&
    parseInt(stats.total_boxes) > 0 &&
    parseInt(links.rows[0].total_links) > 0 &&
    activity.rows[0].last_box_updated;

  output += `Overall Status: ${isWorking ? '✅ WORKING' : '⚠️  NEEDS ATTENTION'}\n`;

  return output;
}

export const check_membox_status_tool = {
  name: 'check_membox_status',
  description: 'Verify if membox system (topic-continuous memory) is working correctly',
  inputSchema: z.object({})
};
```

---

### 7. Optimize Database

**Tool**: `optimize_database`

**Purpose**: Run VACUUM ANALYZE and optimize query performance

**Implementation**:

```typescript
const OptimizeDatabaseSchema = z.object({
  full_vacuum: z.boolean().default(false).describe('Run VACUUM FULL (requires exclusive lock)'),
  reindex: z.boolean().default(false).describe('Rebuild all indexes')
});

export async function optimize_database(
  args: z.infer<typeof OptimizeDatabaseSchema>,
  pool: Pool
): Promise<string> {
  const { full_vacuum, reindex } = args;

  let output = `⚙️  Database Optimization\n\n`;

  try {
    // 1. VACUUM ANALYZE
    output += `Running VACUUM ANALYZE...\n`;
    if (full_vacuum) {
      await pool.query('VACUUM FULL ANALYZE');
      output += `  ✅ VACUUM FULL ANALYZE complete (reclaimed disk space)\n`;
    } else {
      await pool.query('VACUUM ANALYZE');
      output += `  ✅ VACUUM ANALYZE complete (updated statistics)\n`;
    }

    // 2. Reindex if requested
    if (reindex) {
      output += `\nRebuilding indexes...\n`;

      const indexes = [
        'idx_debugging_facts_pheromone',
        'idx_embeddings_hnsw',
        'idx_memory_boxes_pheromone',
        'idx_legal_cases_pheromone'
      ];

      for (const idx of indexes) {
        try {
          await pool.query(`REINDEX INDEX CONCURRENTLY ${idx}`);
          output += `  ✅ ${idx}\n`;
        } catch (err) {
          output += `  ⚠️  ${idx} - ${err.message}\n`;
        }
      }
    }

    // 3. Update table statistics
    output += `\nUpdating statistics...\n`;
    await pool.query('ANALYZE');
    output += `  ✅ Statistics updated\n`;

    output += `\n✅ Database optimization complete!\n`;
  } catch (err) {
    output += `\n❌ Error during optimization: ${err.message}\n`;
  }

  return output;
}

export const optimize_database_tool = {
  name: 'optimize_database',
  description: 'Run VACUUM ANALYZE and optimize query performance',
  inputSchema: OptimizeDatabaseSchema
};
```

---

### 8. Backup Memories

**Tool**: `backup_memories`

**Purpose**: Export memories to JSON for backup

**Implementation**:

```typescript
const BackupMemoriesSchema = z.object({
  output_path: z.string().default('/tmp/mempheromone_backup.json'),
  include_types: z.array(z.string()).default(['debugging_facts', 'claude_memories', 'crystallizations'])
});

export async function backup_memories(
  args: z.infer<typeof BackupMemoriesSchema>,
  pool: Pool
): Promise<string> {
  const { output_path, include_types } = args;

  let output = `💾 Backup Memories\n\n`;

  // Note: Actual file writing would require filesystem access
  // This shows the query structure

  for (const type of include_types) {
    let query: string;
    let count = 0;

    if (type === 'debugging_facts') {
      const result = await pool.query(`SELECT COUNT(*) FROM debugging_facts`);
      count = parseInt(result.rows[0].count);
      output += `  Debugging Facts: ${count} memories\n`;
    } else if (type === 'claude_memories') {
      const result = await pool.query(`SELECT COUNT(*) FROM claude_memories`);
      count = parseInt(result.rows[0].count);
      output += `  Claude Memories: ${count} memories\n`;
    } else if (type === 'crystallizations') {
      const result = await pool.query(`SELECT COUNT(*) FROM crystallization_events`);
      count = parseInt(result.rows[0].count);
      output += `  Crystallizations: ${count} memories\n`;
    }
  }

  output += `\n⚠️  File export requires filesystem access.\n`;
  output += `   Use: python3 scripts/backup_memories.py --output ${output_path}\n`;

  return output;
}

export const backup_memories_tool = {
  name: 'backup_memories',
  description: 'Export memories to JSON for backup (returns backup command)',
  inputSchema: BackupMemoriesSchema
};
```

---

## Installation

### 1. Add to MCP Server

Add these tools to your MCP server's main index:

```typescript
// mcp-server/src/index.ts
import { get_database_stats_tool, get_database_stats } from './tools/db_management/get_database_stats';
import { get_pheromone_distribution_tool, get_pheromone_distribution } from './tools/db_management/get_pheromone_distribution';
import { analyze_memory_quality_tool, analyze_memory_quality } from './tools/db_management/analyze_memory_quality';
import { cleanup_low_quality_memories_tool, cleanup_low_quality_memories } from './tools/db_management/cleanup_low_quality_memories';
import { check_membox_status_tool, check_membox_status } from './tools/db_management/check_membox_status';
import { optimize_database_tool, optimize_database } from './tools/db_management/optimize_database';

// Register tools
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    get_database_stats_tool,
    get_pheromone_distribution_tool,
    analyze_memory_quality_tool,
    cleanup_low_quality_memories_tool,
    rebuild_embeddings_tool,
    check_membox_status_tool,
    optimize_database_tool,
    backup_memories_tool,
    // ... other tools
  ]
}));

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  switch (name) {
    case 'get_database_stats':
      return { content: [{ type: 'text', text: await get_database_stats(args, pool) }] };
    case 'get_pheromone_distribution':
      return { content: [{ type: 'text', text: await get_pheromone_distribution(args, pool) }] };
    case 'analyze_memory_quality':
      return { content: [{ type: 'text', text: await analyze_memory_quality(pool) }] };
    case 'cleanup_low_quality_memories':
      return { content: [{ type: 'text', text: await cleanup_low_quality_memories(args, pool) }] };
    case 'check_membox_status':
      return { content: [{ type: 'text', text: await check_membox_status(pool) }] };
    case 'optimize_database':
      return { content: [{ type: 'text', text: await optimize_database(args, pool) }] };
    // ... other tools
  }
});
```

### 2. Create Tool Files

Create directory structure:

```bash
mcp-server/
├── src/
│   ├── tools/
│   │   ├── db_management/
│   │   │   ├── get_database_stats.ts
│   │   │   ├── get_pheromone_distribution.ts
│   │   │   ├── analyze_memory_quality.ts
│   │   │   ├── cleanup_low_quality_memories.ts
│   │   │   ├── check_membox_status.ts
│   │   │   ├── optimize_database.ts
│   │   │   └── backup_memories.ts
```

---

## Usage Examples

### Daily Health Check

```typescript
// Check overall health
get_database_stats(include_details=true)

// Check pheromone distribution
get_pheromone_distribution(memory_type='all')

// Analyze quality
analyze_memory_quality()

// Check if membox is working
check_membox_status()
```

### Weekly Maintenance

```typescript
// Clean up low-quality memories (dry run first)
cleanup_low_quality_memories(min_pheromone=3.0, min_age_days=90, dry_run=true)

// If satisfied, actually delete
cleanup_low_quality_memories(min_pheromone=3.0, min_age_days=90, dry_run=false)

// Optimize database
optimize_database(full_vacuum=false, reindex=false)
```

### Monthly Deep Clean

```typescript
// Rebuild missing embeddings
rebuild_embeddings(memory_type='all', limit=500)

// Full vacuum (requires exclusive lock - run during off-hours)
optimize_database(full_vacuum=true, reindex=true)

// Backup everything
backup_memories(output_path='/backups/mempheromone_monthly.json')
```

---

## Expected Results

After implementing these tools, you should have:

✅ **Monitoring**: Real-time database health metrics
✅ **Quality Control**: Identify and fix quality issues
✅ **Maintenance**: Automated cleanup and optimization
✅ **Membox Validation**: Verify membox system is working
✅ **Backup/Restore**: Data protection

---

## Next Steps

1. Implement tools in TypeScript
2. Add to MCP server tool registry
3. Test each tool individually
4. Create automated monitoring dashboard
5. Set up cron jobs for weekly maintenance

---

**This is part of the core mempheromone toolkit and should be included in the public repository.**
