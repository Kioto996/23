#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
寻找15元以下有上涨空间的股票（使用东方财富API）
完全绕过AKShare，直接调用东方财富API
"""

import sys
import os
import json
import time
import pandas as pd
from typing import List, Dict, Any
from datetime import datetime

# 添加skills目录到路径
sys.path.insert(0, r'C:\Users\hansu\.workbuddy\skills\stock-analyst\stockai\skills')

# 导入代理管理器
from proxy_manager import get_with_proxy, proxy_manager

# ==================== 配置区域 ====================
# 最高股价（元）
MAX_PRICE = 15.0

# 最低股价（元）
MIN_PRICE = 2.0

# 最小涨幅（%）- 允许小跌，可能反弹
MIN_CHANGE_PCT = -5.0

# 最大涨幅（%）
MAX_CHANGE_PCT = 10.0

# 最小成交额（亿元）
MIN_AMOUNT = 0.3

# 最大分析数量
MAX_ANALYZE = 15

# 是否打印详细日志
VERBOSE = True
# ==================================================


def log(msg: str):
    """打印日志"""
    if VERBOSE:
        print(msg)


def get_all_stocks_from_eastmoney() -> pd.DataFrame:
    """
    从东方财富API获取所有A股实时行情
    使用分页获取全部数据
    """
    log("=" * 80)
    log("步骤1: 从东方财富API获取A股实时行情...")
    log("=" * 80)
    
    all_data = []
    page = 1
    page_size = 500  # 每页500条
    
    try:
        while True:
            # 东方财富API接口（获取沪深A股列表）
            url = "http://82.push2.eastmoney.com/api/qt/clist/get"
            
            params = {
                "pn": str(page),          # 页码
                "pz": str(page_size),     # 每页数量
                "po": "1",
                "np": "1",
                "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                "fltt": "2",
                "invt": "2",
                "fid": "f3",             # 按涨幅排序
                "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",  # A股主板+创业板+科创板
                "fields": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f115,f152"
            }
            
            log(f"正在获取第 {page} 页数据...")
            
            # 使用代理管理器发送请求
            response = get_with_proxy(url, params=params)
            
            if response.status_code != 200:
                log(f"⚠️ 请求失败，状态码: {response.status_code}")
                break
            
            data = response.json()
            
            if not data.get('data') or not data['data'].get('diff'):
                log("✅ 所有数据获取完成")
                break
            
            diff = data['data']['diff']
            all_data.extend(diff)
            
            log(f"✅ 第 {page} 页获取成功，累计 {len(all_data)} 只股票")
            
            # 检查是否还有下一页
            total = data['data'].get('total', 0)
            if len(all_data) >= total:
                log(f"✅ 所有数据获取完成，共 {total} 只股票")
                break
            
            page += 1
            time.sleep(1)  # 延迟，避免被封
        
        # 解析数据到DataFrame
        log(f"\n正在解析 {len(all_data)} 只股票数据...")
        
        parsed_data = []
        for stock in all_data:
            try:
                parsed_data.append({
                    '代码': stock.get('f12', ''),           # 股票代码
                    '名称': stock.get('f14', ''),           # 股票名称
                    '最新价': stock.get('f2', 0) / 100.0 if stock.get('f2') else 0,  # 最新价（需要除以100）
                    '涨跌幅': stock.get('f3', 0) / 100.0 if stock.get('f3') else 0,  # 涨跌幅
                    '涨跌额': stock.get('f4', 0) / 100.0 if stock.get('f4') else 0,
                    '成交量': stock.get('f5', 0),          # 成交量（手）
                    '成交额': stock.get('f6', 0),          # 成交额（元）
                    '振幅': stock.get('f7', 0) / 100.0 if stock.get('f7') else 0,
                    '最高': stock.get('f15', 0) / 100.0 if stock.get('f15') else 0,
                    '最低': stock.get('f16', 0) / 100.0 if stock.get('f16') else 0,
                    '今开': stock.get('f17', 0) / 100.0 if stock.get('f17') else 0,
                    '昨收': stock.get('f18', 0) / 100.0 if stock.get('f18') else 0,
                    '总市值': stock.get('f20', 0),         # 总市值（亿元）
                    '流通市值': stock.get('f21', 0),       # 流通市值（亿元）
                    '换手率': stock.get('f8', 0) / 100.0 if stock.get('f8') else 0,
                    '市盈率': stock.get('f9', 0),          # 市盈率
                    '量比': stock.get('f10', 0) / 100.0 if stock.get('f10') else 0,
                })
            except Exception as e:
                log(f"⚠️ 解析股票数据失败: {e}")
                continue
        
        df = pd.DataFrame(parsed_data)
        log(f"✅ 成功解析 {len(df)} 只股票数据")
        
        return df
        
    except Exception as e:
        log(f"❌ 获取股票列表失败: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


def filter_stocks(df: pd.DataFrame) -> pd.DataFrame:
    """
    筛选股票
    """
    log("\n" + "=" * 80)
    log("步骤2: 筛选股票...")
    log("=" * 80)
    
    if df.empty:
        log("❌ 没有数据")
        return pd.DataFrame()
    
    # 筛选条件
    conditions = (
        (df['最新价'] >= MIN_PRICE) &
        (df['最新价'] <= MAX_PRICE) &
        (df['涨跌幅'] >= MIN_CHANGE_PCT) &
        (df['涨跌幅'] <= MAX_CHANGE_PCT) &
        (df['成交额'] >= MIN_AMOUNT * 100000000)  # 转换为元
    )
    
    filtered_df = df[conditions].copy()
    
    log(f"✅ 筛选前: {len(df)} 只")
    log(f"✅ 筛选后: {len(filtered_df)} 只")
    
    # 按成交额排序（流动性好的优先）
    filtered_df = filtered_df.sort_values(by='成交额', ascending=False)
    
    return filtered_df


def quick_analysis(symbol: str, name: str) -> Dict[str, Any]:
    """
    快速技术分析
    """
    try:
        # 从东方财富获取K线数据
        if symbol.startswith('6'):
            secid = f"1.{symbol}"
        else:
            secid = f"0.{symbol}"
        
        # 获取日K数据（最近30天）
        url = "http://push2his.eastmoney.com/api/qt/stock/kline/get"
        params = {
            "secid": secid,
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            "klt": "101",  # 日K
            "fqt": "1",    # 前复权
            "end": "20500101",
            "lmt": "30"    # 最近30天
        }
        
        response = get_with_proxy(url, params=params)
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        
        if not data.get('data') or not data['data'].get('klines'):
            return None
        
        klines = data['data']['klines']
        
        # 解析K线数据
        parsed_data = []
        for line in klines:
            parts = line.split(',')
            parsed_data.append({
                '日期': parts[0],
                '开盘': float(parts[1]),
                '收盘': float(parts[2]),
                '最高': float(parts[3]),
                '最低': float(parts[4]),
                '成交量': int(parts[5]),
                '成交额': float(parts[6])
            })
        
        df = pd.DataFrame(parsed_data)
        df['日期'] = pd.to_datetime(df['日期'])
        
        if len(df) < 5:
            return None
        
        # 计算技术指标
        latest = df.iloc[-1]
        current_price = latest['收盘']
        
        # 均线
        ma5 = df['收盘'].tail(5).mean()
        ma20 = df['收盘'].tail(20).mean() if len(df) >= 20 else df['收盘'].mean()
        
        # 价格位置
        recent_high = df['最高'].tail(20).max() if len(df) >= 20 else df['最高'].max()
        recent_low = df['最低'].tail(20).min() if len(df) >= 20 else df['最低'].min()
        price_position = (current_price - recent_low) / (recent_high - recent_low) * 100 if recent_high != recent_low else 50
        
        # 成交量趋势
        vol_ma5 = df['成交量'].tail(5).mean()
        latest_vol = latest['成交量']
        volume_ratio = latest_vol / vol_ma5 if vol_ma5 > 0 else 1
        
        # MACD（简单计算）
        ema12 = df['收盘'].ewm(span=12, adjust=False).mean()
        ema26 = df['收盘'].ewm(span=26, adjust=False).mean()
        dif = ema12 - ema26
        dea = dif.ewm(span=9, adjust=False).mean()
        macd_hist = 2 * (dif - dea)
        
        latest_macd_hist = macd_hist.iloc[-1]
        
        # 综合评分（0-100）
        score = 0
        
        # 1. 价格位置（越低越好，0-30分）
        if price_position < 20:
            score += 30
        elif price_position < 40:
            score += 20
        elif price_position < 60:
            score += 10
        
        # 2. 均线趋势（多头排列加分，0-30分）
        if current_price > ma5 > ma20:
            score += 30
        elif current_price > ma20:
            score += 20
        elif current_price > ma5:
            score += 10
        
        # 3. 成交量（放量加分，0-20分）
        if volume_ratio > 2:
            score += 20
        elif volume_ratio > 1.5:
            score += 15
        elif volume_ratio > 1:
            score += 10
        
        # 4. MACD（金叉加分，0-20分）
        if latest_macd_hist > 0:
            score += 20
        elif latest_macd_hist > -0.5:
            score += 10
        
        result = {
            'symbol': symbol,
            'name': name,
            'price': round(current_price, 2),
            'change_pct': round((current_price / df['收盘'].iloc[-2] - 1) * 100, 2) if len(df) > 1 else 0,
            'price_position': round(price_position, 2),
            'ma5': round(ma5, 2),
            'ma20': round(ma20, 2),
            'volume_ratio': round(volume_ratio, 2),
            'macd_hist': round(latest_macd_hist, 4),
            'score': score,
            'source': 'eastmoney_api'
        }
        
        return result
        
    except Exception as e:
        log(f"⚠️ 分析 {symbol}({name}) 失败: {e}")
        return None


def batch_analyze(df: pd.DataFrame, max_count: int = MAX_ANALYZE) -> List[Dict[str, Any]]:
    """
    批量分析股票
    """
    log("=" * 80)
    log(f"步骤3: 批量技术分析（最多分析 {max_count} 只）...")
    log("=" * 80)
    
    results = []
    count = 0
    
    for idx, row in df.iterrows():
        if count >= max_count:
            break
        
        symbol = row['代码']
        name = row['名称']
        
        log(f"\n正在分析 {count + 1}/{max_count}: {symbol}({name})...")
        
        result = quick_analysis(symbol, name)
        
        if result:
            results.append(result)
            count += 1
            log(f"✅ 分析完成，得分: {result['score']}")
            
            # 延迟，避免被封
            time.sleep(1.5)
        else:
            log(f"⚠️ 分析失败，跳过")
    
    return results


def generate_report(results: List[Dict[str, Any]]) -> str:
    """
    生成分析报告
    """
    log("=" * 80)
    log("步骤4: 生成分析报告...")
    log("=" * 80)
    
    if not results:
        return "❌ 没有找到符合条件的股票"
    
    # 按得分排序
    sorted_results = sorted(results, key=lambda x: x['score'], reverse=True)
    
    # 生成Markdown报告
    report = f"""# 15元以下具有上涨空间的股票推荐

## 筛选条件
- 股价: {MIN_PRICE}元 ~ {MAX_PRICE}元
- 涨跌幅: {MIN_CHANGE_PCT}% ~ {MAX_CHANGE_PCT}%
- 成交额: ≥ {MIN_AMOUNT}亿元
- 分析数量: {len(results)} 只

## 推荐股票（按得分排序）

"""
    
    for i, stock in enumerate(sorted_results, 1):
        report += f"""
### {i}. {stock['name']}({stock['symbol']})

- **当前价格**: {stock['price']:.2f} 元
- **技术得分**: {stock['score']}/100
- **价格位置**: {stock['price_position']:.1f}% （近期区间）
- **均线**: MA5={stock['ma5']:.2f}, MA20={stock['ma20']:.2f}
- **量比**: {stock['volume_ratio']:.2f}
- **MACD柱**: {stock['macd_hist']:.4f}
- **数据来源**: {stock['source']}

**研判**:
"""
        
        # 研判意见
        if stock['score'] >= 80:
            report += "- 🟢 **强烈推荐** - 多项指标向好，上涨概率高\n"
        elif stock['score'] >= 60:
            report += "- 🟡 **推荐** - 技术面较好，有上涨空间\n"
        elif stock['score'] >= 40:
            report += "- 🟠 **观望** - 技术面一般，建议观察\n"
        else:
            report += "- 🔴 **谨慎** - 技术面较弱，风险较大\n"
        
        if stock['price_position'] < 30:
            report += "- 💡 价格处于近期低位，有反弹空间\n"
        elif stock['price_position'] > 70:
            report += "- ⚠️ 价格处于近期高位，注意回调风险\n"
        
        if stock['volume_ratio'] > 1.5:
            report += "- 📈 成交量放大，资金关注度高\n"
        
        if stock['macd_hist'] > 0:
            report += "- ✅ MACD金叉，技术面向好\n"
        
        report += "\n---\n"
    
    # 总结
    report += f"""
## 投资建议

1. **优先关注前3只股票**，技术面得分最高
2. **结合基本面分析**，技术面只是参考
3. **控制仓位**，分批买入
4. **设置止损**，避免大幅亏损

---
*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*数据来源: 东方财富API*
"""
    
    return report


def main():
    """主函数"""
    print("=" * 80)
    print("15元以下具有上涨空间的股票筛选系统（东方财富API版）")
    print("=" * 80)
    print("\n配置:")
    print(f"  最高股价: {MAX_PRICE}元")
    print(f"  最低股价: {MIN_PRICE}元")
    print(f"  涨跌幅范围: {MIN_CHANGE_PCT}% ~ {MAX_CHANGE_PCT}%")
    print(f"  最小成交额: {MIN_AMOUNT}亿元")
    print(f"  最大分析数量: {MAX_ANALYZE}只")
    print("\n" + "=" * 80)
    
    # 步骤1: 获取所有股票
    stocks_df = get_all_stocks_from_eastmoney()
    
    if stocks_df.empty:
        print("\n❌ 没有获取到股票数据")
        return
    
    print(f"\n✅ 获取到 {len(stocks_df)} 只股票")
    print("\n前10只股票:")
    print(stocks_df[['代码', '名称', '最新价', '涨跌幅', '成交额']].head(10).to_string())
    
    # 步骤2: 筛选
    filtered_df = filter_stocks(stocks_df)
    
    if filtered_df.empty:
        print("\n❌ 没有找到符合条件的股票")
        return
    
    print(f"\n✅ 找到 {len(filtered_df)} 只符合条件的股票")
    print("\n前10只符合条件的股票:")
    print(filtered_df[['代码', '名称', '最新价', '涨跌幅', '成交额']].head(10).to_string())
    
    # 步骤3: 批量分析
    results = batch_analyze(filtered_df, max_count=MAX_ANALYZE)
    
    if not results:
        print("\n❌ 技术分析失败，没有有效结果")
        return
    
    # 步骤4: 生成报告
    report = generate_report(results)
    
    # 保存报告
    report_file = 'low_price_stocks_report.md'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print("\n" + "=" * 80)
    print(f"✅ 分析报告已保存: {report_file}")
    print("=" * 80)
    
    # 打印报告摘要
    print("\n" + report)
    
    return report


if __name__ == '__main__':
    main()
