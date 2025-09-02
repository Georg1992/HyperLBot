#!/bin/bash
# Fresh Start Cleanup Script
# Removes ALL temporary data ignored by git for completely fresh bot start

echo "🧹 FRESH START CLEANUP - Removing ALL temporary data"
echo "============================================================"

cleanup_count=0

# Function to remove files/directories if they exist
remove_if_exists() {
    if [ -e "$1" ]; then
        if [ -d "$1" ]; then
            file_count=$(find "$1" -type f | wc -l)
            rm -rf "$1"
            echo "🗑️ Removed $1/ directory ($file_count files)"
            cleanup_count=$((cleanup_count + file_count))
        else
            rm -f "$1"
            echo "🗑️ Removed $1"
            cleanup_count=$((cleanup_count + 1))
        fi
    fi
}

# 1. Trading logs directory
remove_if_exists "trading_logs"

# 2. Session metadata files (in root)
for file in session_metadata_*.json; do
    if [ -f "$file" ]; then
        rm -f "$file"
        echo "🗑️ Removed $file"
        cleanup_count=$((cleanup_count + 1))
    fi
done

# 3. Analysis files
for file in analysis_*.json; do
    if [ -f "$file" ]; then
        rm -f "$file"
        echo "🗑️ Removed $file"
        cleanup_count=$((cleanup_count + 1))
    fi
done

# 4. Data directories
remove_if_exists "data/temp"
remove_if_exists "data/cache"
remove_if_exists "data/sessions"
remove_if_exists "data/logs"

# 5. Database files
for file in *.db; do
    if [ -f "$file" ]; then
        rm -f "$file"
        echo "🗑️ Removed $file"
        cleanup_count=$((cleanup_count + 1))
    fi
done

# 6. Runtime state files
runtime_files=(
    "simulated_account.json"
    "open_positions.json"
    "rtm_state.json"
    "bot_instance.lock"
    "trade_history.json"
    "pending_orders.json"
    "session_state.json"
)

for file in "${runtime_files[@]}"; do
    remove_if_exists "$file"
done

# 7. Log files
for file in *.log*; do
    if [ -f "$file" ]; then
        rm -f "$file"
        echo "🗑️ Removed $file"
        cleanup_count=$((cleanup_count + 1))
    fi
done

# 8. Logs directory
remove_if_exists "logs"

# 9. CSV files and exports
for file in *.csv; do
    if [ -f "$file" ]; then
        rm -f "$file"
        echo "🗑️ Removed $file"
        cleanup_count=$((cleanup_count + 1))
    fi
done
remove_if_exists "csv_exports"

# 10. Python cache files
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.pyo" -delete 2>/dev/null || true

echo "============================================================"
if [ $cleanup_count -gt 0 ]; then
    echo "✅ CLEANUP COMPLETE: Removed $cleanup_count files/directories"
    echo "🎯 Bot ready for completely fresh start!"
else
    echo "✅ ALREADY CLEAN: No temporary files found"
fi

echo "🚀 You can now start the bot with completely fresh state!"