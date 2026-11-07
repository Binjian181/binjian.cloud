#!/usr/bin/env bash
# GitHub Actions 流水线：恢复数据 → 抓取/生成 → 提交成果 → 发布 Pages
#
# 用法：scripts/actions_pipeline.sh [fetch|daily]
#
# 分支分工：
#   main      —— 源码，以及精读页 daily/、原创页 article/（正常提交，有历史）
#   site-data —— articles.jsonl 与 seen_urls.txt，单提交强制覆盖，仓库体积不增长
#   gh-pages  —— GitHub Pages 托管的静态站点，同样单提交强制覆盖
set -euo pipefail

TASK="${1:-fetch}"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DATA_BRANCH="${DATA_BRANCH:-site-data}"
PAGES_BRANCH="${PAGES_BRANCH:-gh-pages}"
cd "$REPO_DIR"

# 测试时可覆盖成任意仓库地址（例如本地裸仓库）
ORIGIN_URL="${ORIGIN_URL:-https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}.git}"
export GIT_AUTHOR_NAME=github-actions[bot]
export GIT_AUTHOR_EMAIL=41898282+github-actions[bot]@users.noreply.github.com
export GIT_COMMITTER_NAME="$GIT_AUTHOR_NAME"
export GIT_COMMITTER_EMAIL="$GIT_AUTHOR_EMAIL"

# 建立一个只含单个分支的工作副本，分支不存在时退化为空的孤儿分支
prepare() { # $1=分支 $2=目录
  local branch=$1 dir=$2
  rm -rf "$dir"
  mkdir -p "$dir"
  git -C "$dir" init -q
  git -C "$dir" remote add origin "$ORIGIN_URL"
  if git -C "$dir" fetch -q --depth 1 origin "$branch" 2>/dev/null; then
    git -C "$dir" checkout -q FETCH_HEAD
  else
    echo "   （分支 ${branch} 还不存在，本次首次创建）"
    git -C "$dir" checkout -q --orphan work
  fi
}

push_branch() { # $1=目录 $2=分支 $3=说明
  local dir=$1 branch=$2 msg=$3
  git -C "$dir" add -A
  if git -C "$dir" diff --cached --quiet; then
    echo "   ${branch} 无变化，跳过推送"
    return
  fi
  git -C "$dir" commit -q -m "$msg"
  git -C "$dir" push -q --force origin "HEAD:refs/heads/${branch}"
  echo "   已推送 ${branch}"
}

echo "==> 1/5 恢复文章数据（分支 ${DATA_BRANCH}）"
prepare "$DATA_BRANCH" .state
mkdir -p data
if [ -f .state/articles.jsonl ]; then
  cp .state/articles.jsonl .state/seen_urls.txt data/
else
  : > data/articles.jsonl
  : > data/seen_urls.txt
fi
echo "   现有文章 $(wc -l < data/articles.jsonl) 条，URL 清单 $(wc -l < data/seen_urls.txt) 条"

echo "==> 2/5 执行任务：${TASK}"
case "$TASK" in
  fetch) python scripts/fetch_news.py ;;
  daily) python scripts/daily_people_article_push_v3.py ;;
  *) echo "未知任务：$TASK" && exit 1 ;;
esac

echo "==> 3/5 提交生成物到 main"
git add -A daily article
if git diff --cached --quiet; then
  echo "   main 无变化"
else
  git commit -q -m "${TASK}: $(date -u '+%Y-%m-%d %H:%M') UTC"
  git push -q "$ORIGIN_URL" "HEAD:refs/heads/${GITHUB_REF_NAME:-main}"
  echo "   已推送 main"
fi

echo "==> 4/5 发布 Pages（分支 ${PAGES_BRANCH}）"
prepare "$PAGES_BRANCH" .publish
python scripts/build_site.py .publish
push_branch .publish "$PAGES_BRANCH" "deploy: $(date -u '+%Y-%m-%d %H:%M') UTC"

echo "==> 5/5 回写文章数据（分支 ${DATA_BRANCH}）"
cp data/articles.jsonl data/seen_urls.txt .state/
push_branch .state "$DATA_BRANCH" "data: $(date -u '+%Y-%m-%d %H:%M') UTC"

echo "==> 完成"
