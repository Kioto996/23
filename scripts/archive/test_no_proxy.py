#!/usr/bin/env python3
"""
解决方案：设置 NO_PROXY，让国内金融网站不走代理
"""
import os

# 设置代理（用于访问海外网站）
os.environ['HTTP_PROXY'] = 'http://127.0.0.1:7897'
os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:7897'

# ⚠️ 关键：设置 NO_PROXY，让国内网站不走代理
os.environ['NO_PROXY'] = 'localhost,127.0.0.1,eastmoney.com,10jqka.com.cn,sina.com.cn,qq.com,163.com'

import akshare as ak
import requests

print("=" * 70)
print("测试：设置 NO_PROXY 后访问 akshare")
print(f"HTTP_PROXY: {os.environ.get('HTTP_PROXY')}")
print(f"NO_PROXY: {os.environ.get('NO_PROXY')}")
print("=" * 70)

# 验证：访问东方财富应该不走代理（用国内 IP）
print("\n[验证] 检查当前 IP（应该显示国内 IP）...")
try:
    # 这个请求不走代理（ip-api.com 在国外，但我们先测试国内网站）
    # 直接测试访问东方财富
    test_url = "http://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=5&fs=m:90+t:2&fields=f12,f14,f2,f3"
    
    # requests 会自动遵守 NO_PROXY 设置
    response = requests.get(test_url, timeout=15)
    
    if response.status_code == 200:
        print("✓✓✓ 成功访问东方财富 API！✓✓✓")
        print(f"  返回数据: {response.text[:200]}")
    else:
        print(f"✗ 访问失败: HTTP {response.status_code}")
        
except Exception as e:
    print(f"✗ 访问失败: {e}")

# 测试：用 akshare 获取板块资金流
print("\n" + "="*70)
print("[测试] 用 akshare 获取板块资金流（今日）...")
try:
    df = ak.stock_sector_fund_flow_rank(indicator="今日")
    print("✓✓✓ 获取成功！✓✓✓")
    print(f"  数据形状: {df.shape}")
    print(f"  总板块数: {len(df)}")
    print("\n  前10名板块:")
    print(df.head(10).to_string(index=False))
    
    # 保存
    output_file = "V:/psy/psy/stock/板块资金流_真实数据.csv"
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n  ✓ 数据已保存到: {output_file}")
    print("\n  🎉🎉🎉 成功获取真实资金流数据！🎉🎉🎉")
    
except Exception as e:
    print(f"✗ 获取失败: {e}")
    import traceback
    traceback.print_exc()

# 测试：获取涨停板数据（验证不受影响）
print("\n" + "="*70)
print("[验证] 获取涨停板数据（验证功能正常）...")
try:
    from datetime import datetime
    today = datetime.now().strftime("%Y%m%d")
    df_zt = ak.stock_zt_pool_em(date=today)
    print(f"✓ 获取成功! 涨停股票数: {len(df_zt)}")
except Exception as e:
    print(f"✗ 获取失败: {e}")

print("\n" + "="*70)
print("测试完成")
print("="*70)

print("\n【结论】")
if 'df' in locals() and not df.empty:
    print("🎉 成功！现在可以改写 stock_observation_system_v3.py")
    print("  → 用真实的板块资金流数据替换估算方法")
else:
    print("❌ 还是失败，需要进一步排查")
    print("  可能的原因:")
    print("  1. NO_PROXY 设置没生效")
    print("  2. 需要重启 Python 才能让环境变量生效")
    print("  3. akshare 内部用了其他网络库（非 requests）")
