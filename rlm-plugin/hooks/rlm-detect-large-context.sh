#!/bin/bash
# RLM Large Context Detection Hook
# Detects when user references large files and triggers RLM mode

set -euo pipefail

# Read input from stdin
input=$(cat)

# Extract user prompt
user_prompt=$(echo "$input" | jq -r '.user_prompt // ""')

# Threshold for RLM activation (100KB)
SIZE_THRESHOLD=102400

# Function to check file size (cross-platform)
check_file_size() {
    local file="$1"
    if [ -f "$file" ]; then
        # Try Linux stat first, then macOS
        local size=$(stat --format=%s "$file" 2>/dev/null || stat -f%z "$file" 2>/dev/null || wc -c < "$file" 2>/dev/null || echo 0)
        echo "$size"
    else
        echo 0
    fi
}

# Extract potential file paths from the prompt
# Look for patterns like /path/to/file, ./file, ~/file
# Use Perl regex for better path matching including hyphens and special chars
file_paths=$(echo "$user_prompt" | grep -oP '(~|\.\.?)?/[a-zA-Z0-9_\-\./]+\.[a-zA-Z0-9]+' 2>/dev/null | head -20 || true)

# Also try to match quoted paths
quoted_paths=$(echo "$user_prompt" | grep -oP "(?<=['\"])[^'\"]+(?=['\"])" 2>/dev/null | grep -E '^\/' 2>/dev/null | head -10 || true)

# Combine both (handle empty cases)
if [ -n "$quoted_paths" ]; then
    file_paths=$(printf '%s\n%s' "$file_paths" "$quoted_paths" | sort -u)
fi

large_file_found=""
large_file_size=0

for path in $file_paths; do
    # Expand ~ to home directory
    expanded_path="${path/#\~/$HOME}"

    if [ -f "$expanded_path" ]; then
        size=$(check_file_size "$expanded_path")
        if [ "$size" -gt "$SIZE_THRESHOLD" ]; then
            large_file_found="$expanded_path"
            large_file_size=$size
            break
        fi
    fi
done

# Also check for keywords that suggest large context processing
needs_rlm=false
if [ -n "$large_file_found" ]; then
    needs_rlm=true
elif echo "$user_prompt" | grep -qiE '(large file|huge file|big file|massive|10mb|100mb|1gb|millions of lines|thousands of lines|entire codebase|all files in|whole project)'; then
    needs_rlm=true
fi

if [ "$needs_rlm" = true ]; then
    # Format file size for display
    if [ "$large_file_size" -gt 1048576 ]; then
        size_display="$(( large_file_size / 1048576 ))MB"
    elif [ "$large_file_size" -gt 1024 ]; then
        size_display="$(( large_file_size / 1024 ))KB"
    else
        size_display="${large_file_size} bytes"
    fi

    if [ -n "$large_file_found" ]; then
        file_info="File detected: $large_file_found ($size_display)"
    else
        file_info="Large context keywords detected in prompt"
    fi

    cat << EOF
{
  "continue": true,
  "systemMessage": "## RLM MODE ACTIVATED\n\n$file_info\n\n**Use Recursive Language Model approach:**\n\n\`\`\`bash\ncd \${CLAUDE_PLUGIN_ROOT}/scripts && python3 << 'PYEOF'\nfrom rlm_runner import RLMRunner\nimport json\n\nrunner = RLMRunner(verbose=True)\nresult = runner.load('FILE_PATH_HERE')\nprint(json.dumps(result, indent=2))\n\n# Probe context\nresult = runner.execute('''\nprint(f'Total length: {len(context)} characters')\nprint(f'First 500 chars: {context[:500]}')\n''')\nprint(result['output'])\nPYEOF\n\`\`\`\n\n**Key functions:**\n- \`llm_query(prompt)\` - Query sub-LLM (Haiku) on chunks\n- \`llm_query_batch(prompts)\` - Batch multiple queries\n- \`context\` variable holds loaded content\n\n**Chunking strategies:**\n- By size: \`context[i*chunk_size:(i+1)*chunk_size]\`\n- By lines: \`context.split('\\\\n')\`\n- By sections: \`re.split(r'###', context)\`"
}
EOF
else
    # No large context detected, continue normally
    cat << 'EOF'
{
  "continue": true
}
EOF
fi
