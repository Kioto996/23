"""
市场状态分类系统 (Regime Analysis)
根据每日涨停数+上证涨跌+板块热度自动判断市场状态
不同状态下使用不同的策略参数
"""

import os, time, requests, json, datetime
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""
import akshare as ak

def classify_regime(zt_count, sh_chg):
    """
    根据涨停数和上证涨跌分类市场状态
    """
    if zt_count >= 80 and sh_chg > 0.5:
        return "强势", 1.0   # 状态名, 仓位系数
    elif zt_count >= 80:
        return "强势_平", 0.8
    elif zt_count >= 60:
        return "活跃", 0.7
    elif zt_count >= 40:
        return "震荡", 0.5
    elif zt_count >= 20:
        return "低迷", 0.3
    else:
        return "冰点", 0.0

def get_regime_params(regime):
    """
    不同市场状态下的策略参数
    """
    params = {
        "强势":     {"vol_threshold": 1.5, "position_pct": 0.4, "weekly_max": 3, "dev_range": (-5, 3)},
        "强势_平":  {"vol_threshold": 1.8, "position_pct": 0.35, "weekly_max": 2, "dev_range": (-5, 3)},
        "活跃":     {"vol_threshold": 2.0, "position_pct": 0.30, "weekly_max": 2, "dev_range": (-5, 3)},
        "震荡":     {"vol_threshold": 2.0, "position_pct": 0.25, "weekly_max": 1, "dev_range": (-5, 1)},
        "低迷":     {"vol_threshold": 2.5, "position_pct": 0.15, "weekly_max": 1, "dev_range": (-3, 1)},
        "冰点":     {"vol_threshold": 99,  "position_pct": 0.0,  "weekly_max": 0, "dev_range": (-5, 3)},
    }
    return params.get(regime, params["震荡"])

def get_today_regime():
    """获取今日市场状态"""
    today = datetime.date.today().strftime("%Y%m%d")
    try:
        zt = ak.stock_zt_pool_em(date=today)
        zt_count = len(zt)
        time.sleep(0.2)
        
        r = requests.get("https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketData.getKLineData?symbol=sh000001&scale=240&ma=no&datalen=5", timeout=8)
        sh = r.json()
        last = sh[-1]
        sh_chg = (float(last["close"]) - float(last["open"])) / float(last["open"]) * 100
        
        regime, position = classify_regime(zt_count, sh_chg)
        params = get_regime_params(regime)
        
        return {
            "date": today,
            "zt_count": zt_count,
            "sh_change": round(sh_chg, 1),
            "regime": regime,
            "position_ratio": position,
            "params": params
        }
    except Exception as e:
        return {"error": str(e)}

# 如果直接运行则打印今日状态
if __name__ == "__main__":
    result = get_today_regime()
    if "error" not in result:
        print(f"📊 市场状态: {result['regime']}")
        print(f"   涨停 {result['zt_count']}只 | 上证 {result['sh_change']:+.1f}%")
        print(f"   仓位系数: ×{result['position_ratio']}")
        print(f"   策略参数:")
        p = result['params']
        print(f"     放量阈值: >{p['vol_threshold']}x 均量")
        print(f"     单票仓位: ≤{p['position_pct']*100:.0f}%")
        print(f"     周交易上限: {p['weekly_max']}次")
        print(f"     偏离区间: {p['dev_range'][0]}%~{p['dev_range'][1]}%")
    else:
        print("获取失败:", result["error"])
