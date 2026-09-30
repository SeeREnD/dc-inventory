#!/usr/bin/env bash
# 自动把 dc-inventory 项目代码提交并推送到 GitHub 做备份
# 由 crontab 定时调用；无变更时直接退出
set -u

REPO="/home/jiwi/projects/dc-inventory"
LOG="/tmp/dc-inventory-git-backup.log"

cd "$REPO" || exit 1

# 无变更则退出
if [ -z "$(git status --porcelain)" ]; then
  exit 0
fi

{
  echo "===== $(date '+%F %T') 检测到变更，自动提交 ====="
  git add -A
  git commit -m "chore: 自动备份 $(date '+%F %T')"
  git push origin main
  echo
} >> "$LOG" 2>&1

# 日志只保留最近 200 行，防止无限增长
tail -200 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
