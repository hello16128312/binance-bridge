#!/bin/bash
# 最简诊断脚本 - 测试GitHub Actions环境
echo "=== 环境信息 ==="
echo "OS: $(uname -a)"
echo "Python: $(python3 --version)"
echo "PWD: $(pwd)"
echo "Internet: $(curl -s --max-time 5 'https://api.binance.com/api/v3/time' || echo 'BINANCE FAILED')"
echo "Internet2: $(curl -s --max-time 5 'https://eapi.binance.com/eapi/v1/time' || echo 'EAPI FAILED')"
echo "Internet3: $(curl -s --max-time 5 'https://www.google.com' -o /dev/null -w '%{http_code}')"
echo "=== DNS ==="
nslookup api.binance.com 2>&1 || true
nslookup eapi.binance.com 2>&1 || true
echo "DONE"
