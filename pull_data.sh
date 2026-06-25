#!/bin/bash
# Binance Bridge — 一键部署脚本
# 自动拉取GitHub Actions获取的Binance期权数据
set -e

REPO_DIR="$HOME/workspace/binance-bridge"

echo "📡 拉取最新Binance数据..."
cd "$REPO_DIR"
git pull origin main 2>&1

echo ""
echo "📊 数据文件:"
ls -lh data/ 2>&1

# 如果有新数据，自动复制到双波动率锥目录
if [ -f "data/btc_option_tickers.json" ]; then
    cp data/btc_option_tickers.json /tmp/binance_btc_options.json
    cp data/eth_option_tickers.json /tmp/binance_eth_options.json 2>/dev/null
    echo "✅ 数据已同步到 /tmp/"
fi

echo ""
echo "🔄 下次自动更新: 每1小时 (GitHub Actions schedule)"
