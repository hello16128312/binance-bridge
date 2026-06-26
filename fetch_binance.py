#!/usr/bin/env python3
"""
GitHub Actions 中运行的 Binance 期权数据获取脚本 v2
增加详细诊断 + 多endpoint容错
"""
import json, urllib.request, os, time, sys, traceback

OUTPUT_DIR = "data"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 尝试多个Binance endpoint
BINANCE_BASES = [
    "https://eapi.binance.com",
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
]


def http_get(url, timeout=15):
    """HTTP GET with retry"""
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; BinanceBridge/1.0)",
        "Accept": "application/json",
    })
    for attempt in range(3):
        try:
            resp = urllib.request.urlopen(req, timeout=timeout)
            return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            print(f"    HTTP {e.code}: {e.reason}")
            if e.code == 451:  # 地区限制
                return None
            time.sleep(2)
        except Exception as e:
            print(f"    错误: {e}")
            time.sleep(2)
    return None


def find_working_base():
    """找到可用的Binance endpoint"""
    for base in BINANCE_BASES:
        print(f"  测试 {base} ...")
        result = http_get(f"{base}/api/v3/time", timeout=8)
        if result and "serverTime" in result:
            print(f"  ✅ {base} 可用, serverTime={result['serverTime']}")
            return base
        # 也试期权端点
        result = http_get(f"{base}/eapi/v1/time", timeout=8)
        if result and "serverTime" in result:
            print(f"  ✅ {base} (期权端点) 可用")
            return base
        print(f"  ❌ {base} 不可用")
    return None


def main():
    print("=" * 60)
    print("  Binance 期权数据获取 v2 (GitHub Actions)")
    print(f"  Python {sys.version}")
    print("=" * 60)

    # 1. 找到可用endpoint
    print("\n🔍 扫描可用endpoint...")
    base = find_working_base()
    if not base:
        print("❌ 所有endpoint不可用!")
        return 1

    # 2. 获取服务器时间
    print(f"\n📡 使用 {base}")
    t = http_get(f"{base}/eapi/v1/time")
    if t:
        print(f"  ✅ 连接成功: serverTime={t.get('serverTime','?')}")
    else:
        print("  ⚠ 期权端点不可用, 尝试现货端点...")
        t = http_get(f"{base}/api/v3/time")
        if t:
            print(f"  ✅ 现货端点可用, 用现货API获取基础数据")

    # 3. 获取BTC期权指数
    print("\n📊 获取 BTC 期权指数价...")
    btc_index = http_get(f"{base}/eapi/v1/index?underlying=BTCUSDT")
    if btc_index:
        with open(f"{OUTPUT_DIR}/btc_index.json", "w") as f:
            json.dump(btc_index, f, indent=2)
        print(f"  ✅ BTC指数价: {btc_index.get('indexPrice','?')}")

    # 4. 获取所有BTC期权的Ticker (含IV!)
    print("\n📊 获取 BTC 期权 Ticker...")
    all_tickers = []
    for page in range(1, 30):
        data = http_get(f"{base}/eapi/v1/ticker?page={page}&limit=100", timeout=20)
        if not data or not isinstance(data, list) or len(data) == 0:
            break
        all_tickers.extend(data)
        print(f"  第{page}页: {len(data)}条, 累计{len(all_tickers)}条")
        time.sleep(0.3)

    if all_tickers:
        with open(f"{OUTPUT_DIR}/btc_option_tickers.json", "w") as f:
            json.dump(all_tickers, f, indent=2)
        print(f"  ✅ 共 {len(all_tickers)} 条BTC期权Ticker")
        ivs = [float(t.get("markIV", 0)) for t in all_tickers if float(t.get("markIV", 0)) > 0]
        if ivs:
            print(f"  有效IV: {len(ivs)}条, 范围 {min(ivs):.1%}~{max(ivs):.1%}, 均值 {sum(ivs)/len(ivs):.1%}")
    else:
        print("  ⚠ 未获取到BTC期权Ticker")

    # 5. ETH期权
    print("\n📊 获取 ETH 期权 Ticker...")
    eth_tickers = http_get(f"{base}/eapi/v1/ticker?underlying=ETHUSDT&limit=500", timeout=20)
    if eth_tickers:
        with open(f"{OUTPUT_DIR}/eth_option_tickers.json", "w") as f:
            json.dump(eth_tickers, f, indent=2)
        print(f"  ✅ {len(eth_tickers)} 条ETH期权Ticker")
    else:
        print("  ⚠ 未获取到ETH期权Ticker")

    # 6. 获取exchangeInfo
    print("\n📊 获取 期权合约信息...")
    exchange_info = http_get(f"{base}/eapi/v1/exchangeInfo")
    if exchange_info:
        with open(f"{OUTPUT_DIR}/exchange_info.json", "w") as f:
            json.dump(exchange_info, f, indent=2)
        symbols = exchange_info.get("symbols", [])
        option_symbols = [s for s in symbols if s.get("contractType") in ("CALL", "PUT")]
        print(f"  ✅ 期权合约: {len(option_symbols)}个")

    # 7. 汇总
    print(f"\n{'='*60}")
    print(f"  数据保存到 {OUTPUT_DIR}/")
    for f in sorted(os.listdir(OUTPUT_DIR)):
        size = os.path.getsize(os.path.join(OUTPUT_DIR, f))
        print(f"    {f}: {size:,} bytes")
    print(f"{'='*60}")

    return 0 if all_tickers else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\n❌ 未捕获异常: {e}")
        traceback.print_exc()
        sys.exit(1)
