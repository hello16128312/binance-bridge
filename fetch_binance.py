#!/usr/bin/env python3
"""
GitHub Actions 中运行的 Binance 期权数据获取脚本
运行在境外 Azure VM 上，不受 GFW 限制
"""
import json, urllib.request, os, time

BINANCE_BASE = "https://eapi.binance.com"
OUTPUT_DIR = "data"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def binance_get(endpoint):
    url = f"{BINANCE_BASE}{endpoint}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(3):
        try:
            resp = urllib.request.urlopen(req, timeout=30)
            return json.loads(resp.read())
        except Exception as e:
            print(f"  重试 {attempt+1}/3: {e}")
            time.sleep(2)
    return None


def main():
    print("=" * 50)
    print("  Binance 期权数据获取 (GitHub Actions)")
    print("=" * 50)

    # 1. 获取服务器时间
    t = binance_get("/eapi/v1/time")
    if t:
        print(f"✅ Binance连接成功: serverTime={t.get('serverTime','?')}")
    else:
        print("❌ Binance连接失败")
        return 1

    # 2. 获取BTC期权信息
    print("\n📊 获取 BTC 期权...")
    btc_info = binance_get("/eapi/v1/exchangeInfo")
    if btc_info:
        # 保存完整 exchangeInfo
        with open(f"{OUTPUT_DIR}/btc_exchange_info.json", "w") as f:
            json.dump(btc_info, f, indent=2)
        
        # 统计期权合约
        symbols = btc_info.get("symbols", [])
        option_symbols = [s for s in symbols if s.get("contractType") in ("CALL", "PUT")]
        print(f"  总交易对: {len(symbols)}")
        print(f"  期权合约: {len(option_symbols)}")
        
        # 统计到期日
        from collections import Counter
        expiries = Counter()
        underlying = Counter()
        for s in option_symbols:
            if "expiryDate" in s:
                exp = str(s["expiryDate"])[:8]
                expiries[exp] += 1
            underlying[s.get("underlying", "?")] += 1
        
        print(f"  标的分布: {dict(underlying)}")
        print(f"  到期日: {len(expiries)}个")
        for exp, cnt in sorted(expiries.items()):
            print(f"    {exp}: {cnt}个合约")

    # 3. 获取BTC期权指数价
    print("\n📊 获取 BTC 期权指数价...")
    btc_index = binance_get("/eapi/v1/index?underlying=BTCUSDT")
    if btc_index:
        with open(f"{OUTPUT_DIR}/btc_index.json", "w") as f:
            json.dump(btc_index, f, indent=2)
        print(f"  BTC指数价: {btc_index.get('indexPrice','?')}")

    # 4. 获取所有BTC期权的Ticker (含IV!)
    print("\n📊 获取 BTC 期权 Ticker (含IV)...")
    all_tickers = []
    # 分页获取
    for page in range(1, 21):
        data = binance_get(f"/eapi/v1/ticker?page={page}&limit=100")
        if not data or not isinstance(data, list) or len(data) == 0:
            break
        all_tickers.extend(data)
        print(f"  第{page}页: {len(data)}条, 累计{len(all_tickers)}条")
        time.sleep(0.5)  # 限流
    
    if all_tickers:
        with open(f"{OUTPUT_DIR}/btc_option_tickers.json", "w") as f:
            json.dump(all_tickers, f, indent=2)
        print(f"  ✅ 共获取 {len(all_tickers)} 条BTC期权Ticker")
        
        # 统计IV数据
        ivs = []
        for t in all_tickers:
            iv = float(t.get("markIV", 0))
            if iv > 0:
                ivs.append(iv)
        if ivs:
            print(f"  有效IV: {len(ivs)}条")
            print(f"  IV范围: {min(ivs):.1%} ~ {max(ivs):.1%}")
            print(f"  IV均值: {sum(ivs)/len(ivs):.1%}")

    # 5. 获取ETH期权Ticker
    print("\n📊 获取 ETH 期权 Ticker...")
    eth_tickers = binance_get("/eapi/v1/ticker?underlying=ETHUSDT&limit=500")
    if eth_tickers:
        with open(f"{OUTPUT_DIR}/eth_option_tickers.json", "w") as f:
            json.dump(eth_tickers, f, indent=2)
        print(f"  ✅ 获取 {len(eth_tickers)} 条ETH期权Ticker")
    
    # 6. 保存行情摘要
    print(f"\n✅ 所有数据已保存到 {OUTPUT_DIR}/ ")
    print(f"  文件列表:")
    for f in sorted(os.listdir(OUTPUT_DIR)):
        size = os.path.getsize(os.path.join(OUTPUT_DIR, f))
        print(f"    {f}: {size:,} bytes")
    
    return 0


if __name__ == "__main__":
    exit(main())
