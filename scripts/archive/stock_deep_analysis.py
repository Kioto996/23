# -*- coding: utf-8 -*-
"""深度技术分析 - 对候选股做K线+资金+持仓分析"""
import akshare as ak
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime, timedelta

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

LOG_FILE = os.path.join(OUT_DIR, 'analysis_log.txt')
def log(msg):
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg, flush=True)

open(LOG_FILE, 'w').close()
log(f"START: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# 候选股列表 - 从今日资金流和技术面精选
CANDIDATES = [
    # (code, name, today_change, reason)
    ('300502', '新易盛', 5.11, 'CPO光模块龙头,特大单净流入14.74亿,涨幅仅5%未涨停'),
    ('000066', '中国长城', 8.38, '国产替代,特大单净流入12.68亿'),
    ('300265', '通光线缆', 20.00, '光通信电缆,特大单净流入7.58亿,今日涨停但可能连板'),
    ('000591', '太阳能', 9.96, '公用事业+光伏,特大单净流入5.18亿,接近涨停'),
    ('601179', '中国西电', 6.08, '电力设备,特大单净流入5.51亿'),
    ('600089', '特变电工', 3.43, '电力设备+变压器,特大单净流入6.23亿'),
    ('002129', 'TCL中环', 5.83, '光伏硅片,特大单净流入6.48亿'),
    ('600276', '恒瑞医药', 4.84, '创新药龙头,特大单净流入9.80亿'),
    ('300782', '卓胜微', 2.34, '射频芯片,特大单净流入4.49亿'),
    ('601899', '紫金矿业', 0.90, '黄金龙头,特大单净流入4.24亿,低涨幅高资金'),
]

def calc_ma(series, periods=[5, 10, 20, 60]):
    result = {}
    for p in periods:
        result[f'MA{p}'] = round(series.rolling(p).mean().iloc[-1], 2)
    return result

def calc_rsi(close, periods=[6, 12, 24]):
    result = {}
    for p in periods:
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(p).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(p).mean()
        rs = gain / loss
        result[f'RSI{p}'] = round(100 - (100 / (1 + rs)), 2) if rs.iloc[-1] != np.inf and not pd.isna(rs.iloc[-1]) else 50.0
    return result

def calc_macd(close, fast=12, slow=26, signal=9):
    ema_fast = close.ewm(span=fast).mean()
    ema_slow = close.ewm(span=slow).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal).mean()
    hist = 2 * (dif - dea)
    return {
        'DIF': round(dif.iloc[-1], 3),
        'DEA': round(dea.iloc[-1], 3),
        'MACD_hist': round(hist.iloc[-1], 3),
        'DIF_prev': round(dif.iloc[-2], 3),
        'MACD_hist_prev': round(hist.iloc[-2], 3),
        'golden_cross': 'DIF上穿DEA' if dif.iloc[-1] > dea.iloc[-1] and dif.iloc[-2] <= dea.iloc[-2] else ('多头' if dif.iloc[-1] > dea.iloc[-1] else '空头'),
    }

def calc_kdj(high, low, close, n=9, m1=3, m2=3):
    low_n = low.rolling(n).min()
    high_n = high.rolling(n).max()
    rsv = (close - low_n) / (high_n - low_n) * 100
    k = rsv.ewm(com=m1-1).mean()
    d = k.ewm(com=m2-1).mean()
    j = 3 * k - 2 * d
    return {
        'K': round(k.iloc[-1], 2),
        'D': round(d.iloc[-1], 2),
        'J': round(j.iloc[-1], 2),
        'signal': '超买' if j.iloc[-1] > 100 else ('超卖' if j.iloc[-1] < 0 else '中性'),
    }

def analyze_stock(code, name, today_chg, reason):
    """对单只股票做全面技术分析"""
    log(f"\n{'='*50}")
    log(f"分析: {name}({code}) - 今日涨幅{today_chg}%")
    log(f"逻辑: {reason}")

    result = {'code': code, 'name': name, 'today_change': today_chg, 'reason': reason}

    try:
        # 获取120日K线
        end_date = '20260512'
        start_date = '20251115'
        df = ak.stock_zh_a_hist(symbol=code, period="daily",
                                start_date=start_date, end_date=end_date, adjust="qfq")
        if df is None or len(df) < 30:
            log(f"  [ERR] K线数据不足")
            return None

        close = df['收盘']
        high = df['最高']
        low = df['最低']
        volume = df['成交量']
        latest = df.iloc[-1]
        prev = df.iloc[-2]

        # 基本信息
        result['price'] = float(latest['收盘'])
        result['high'] = float(latest['最高'])
        result['low'] = float(latest['最低'])
        result['open'] = float(latest['开盘'])
        result['volume'] = float(latest['成交量'])
        result['volume_ma5'] = float(volume.rolling(5).mean().iloc[-1])
        result['vol_ratio'] = round(result['volume'] / result['volume_ma5'], 2)

        # 均线系统
        mas = calc_ma(close)
        result.update(mas)
        log(f"  价格:{result['price']} MA5:{mas['MA5']} MA10:{mas['MA10']} MA20:{mas['MA20']} MA60:{mas['MA60']}")

        # 均线多头/空头排列
        ma_vals = [mas['MA5'], mas['MA10'], mas['MA20'], mas['MA60']]
        bullish_ma = ma_vals[0] > ma_vals[1] > ma_vals[2]  # 短中长均线多头排列
        result['ma_alignment'] = '多头排列' if bullish_ma else ('空头排列' if ma_vals[0] < ma_vals[1] < ma_vals[2] else '交叉')
        log(f"  均线: {result['ma_alignment']}")

        # 站上/跌破均线
        price = result['price']
        result['above_ma5'] = price > mas['MA5']
        result['above_ma20'] = price > mas['MA20']
        log(f"  站上MA5:{result['above_ma5']} 站上MA20:{result['above_ma20']}")

        # RSI
        rsi = calc_rsi(close)
        result.update(rsi)
        log(f"  RSI: {rsi['RSI6']}/{rsi['RSI12']}/{rsi['RSI24']}")

        # MACD
        macd = calc_macd(close)
        result.update(macd)
        log(f"  MACD: DIF={macd['DIF']} DEA={macd['DEA']} 柱={macd['MACD_hist']} {macd['golden_cross']}")

        # KDJ
        kdj = calc_kdj(high, low, close)
        result.update(kdj)
        log(f"  KDJ: K={kdj['K']} D={kdj['D']} J={kdj['J']} {kdj['signal']}")

        # 近5日趋势
        recent_5 = df.tail(5)
        chg_5d = (recent_5['收盘'].iloc[-1] / recent_5['收盘'].iloc[0] - 1) * 100
        result['chg_5d'] = round(chg_5d, 2)
        log(f"  近5日涨幅: {chg_5d:.2f}%")

        # 近20日涨幅
        recent_20 = df.tail(20)
        chg_20d = (recent_20['收盘'].iloc[-1] / recent_20['收盘'].iloc[0] - 1) * 100
        result['chg_20d'] = round(chg_20d, 2)
        log(f"  近20日涨幅: {chg_20d:.2f}%")

        # 距离压力位/支撑位（近60日高点低点）
        high_60d = float(df.tail(60)['最高'].max())
        low_60d = float(df.tail(60)['最低'].min())
        result['high_60d'] = high_60d
        result['low_60d'] = low_60d
        result['resistance_pct'] = round((high_60d - price) / price * 100, 2)  # 距压力位百分比
        result['support_pct'] = round((price - low_60d) / price * 100, 2)  # 距支撑位百分比
        log(f"  压力位:{high_60d}(+{result['resistance_pct']}%) 支撑位:{low_60d}(-{result['support_pct']}%)")

        # 连续上涨天数
        consec_up = 0
        for i in range(len(df)-1, 0, -1):
            if df['收盘'].iloc[i] > df['收盘'].iloc[i-1]:
                consec_up += 1
            else:
                break
        result['consec_up_days'] = consec_up
        log(f"  连涨天数: {consec_up}")

        # 放量判断
        result['volume_surge'] = result['vol_ratio'] > 2.0
        log(f"  量比: {result['vol_ratio']} {'放量!' if result['volume_surge'] else ''}")

        # 综合评分
        score = 0
        signals = []

        # 1. 均线多头排列 (+20)
        if result['ma_alignment'] == '多头排列':
            score += 20
            signals.append('均线多头排列(+20)')
        elif result['above_ma5'] and result['above_ma20']:
            score += 10
            signals.append('站上MA5/MA20(+10)')

        # 2. MACD金叉/多头 (+15)
        if macd['golden_cross'] == 'DIF上穿DEA':
            score += 15
            signals.append('MACD金叉(+15)')
        elif macd['golden_cross'] == '多头':
            score += 10
            signals.append('MACD多头(+10)')

        # 3. RSI适中 (30-70) (+15)
        if 40 <= rsi['RSI6'] <= 70:
            score += 15
            signals.append(f'RSI适中({rsi["RSI6"]})(+15)')
        elif rsi['RSI6'] < 40:
            score += 10
            signals.append(f'RSI偏低({rsi["RSI6"]})(+10)')
        else:
            signals.append(f'RSI偏高({rsi["RSI6"]})(+0)')

        # 4. KDJ未超买 (+10)
        if kdj['J'] < 100:
            score += 10
            signals.append(f'KDJ未超买(J={kdj["J"]})(+10)')

        # 5. 放量上涨 (+10)
        if result['vol_ratio'] > 1.5:
            score += 10
            signals.append(f'放量(量比{result["vol_ratio"]})(+10)')

        # 6. 距压力位空间 > 8% (+15)
        if result['resistance_pct'] >= 8:
            score += 15
            signals.append(f'压力位空间{result["resistance_pct"]}%(+15)')
        elif result['resistance_pct'] >= 5:
            score += 8
            signals.append(f'压力位空间{result["resistance_pct"]}%(+8)')

        # 7. 近期趋势 (+15)
        if 0 < result['chg_5d'] < 15:
            score += 15
            signals.append(f'近5日涨{result["chg_5d"]}%(+15)')
        elif result['chg_5d'] >= 15:
            score += 5
            signals.append(f'近5日涨{result["chg_5d"]}%-短期涨幅过大(+5)')

        # 8. 涨幅适中（今日涨2-7%） (+10)
        if 2 <= today_chg <= 7:
            score += 10
            signals.append(f'今日涨幅适中{today_chg}%(+10)')
        elif today_chg >= 10:
            score -= 10
            signals.append(f'今日涨停-追高风险(-10)')

        # 9. 未连涨过多 (+5)
        if consec_up <= 3:
            score += 5
            signals.append(f'连涨{consec_up}天(+5)')
        elif consec_up >= 5:
            score -= 10
            signals.append(f'连涨{consec_up}天-短期过热(-10)')

        result['score'] = score
        result['signals'] = signals
        log(f"\n  >>> 综合评分: {score}/100")
        for s in signals:
            log(f"      {s}")

        return result

    except Exception as e:
        log(f"  [ERR] {type(e).__name__}: {e}")
        return None

# === 主流程 ===
results = []
for code, name, chg, reason in CANDIDATES:
    r = analyze_stock(code, name, chg, reason)
    if r:
        results.append(r)

# 按评分排序
results.sort(key=lambda x: x['score'], reverse=True)

log(f"\n\n{'='*60}")
log("最终排名:")
for i, r in enumerate(results):
    log(f"  #{i+1} {r['name']}({r['code']}) 评分:{r['score']} 今日涨:{r['today_change']}% 价格:{r['price']}")

# 保存结果
path = os.path.join(OUT_DIR, 'candidate_analysis.json')
with open(path, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

log(f"\nDONE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
