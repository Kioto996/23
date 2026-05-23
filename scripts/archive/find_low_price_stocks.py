#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
寻找15元以下有上涨空间的股票
使用多维度分析：技术指标、成交量、涨跌幅、换手率等
"""

import sys
import os
import time
import pandas as pd
from typing import List, Dict, Any

# 添加skills目录到路径
sys.path.insert(0, r'C:\Users\hansu\.workbuddy\skills\stock-analyst\stockai\skills')

# 导入自定义模块
from akshare_enhanced import ak_enhanced
from technical_analysis import TechnicalAnalyzer, integrate_technical_to_report

# ==================== 配置区域 ====================
# 最高股价（元）
MAX_PRICE = 15.0

# 最低股价（元）- 避免退市风险股
MIN_PRICE = 2.0

# 最小涨幅（%）- 今日必须上涨
MIN_CHANGE_PCT = 0.0

# 最大涨幅（%）- 避免已经暴涨的
MAX_CHANGE_PCT = 10.0

# 最小成交额（亿元）- 避免流动性差的
MIN_AMOUNT = 0.5

# 最大分析股票数量（避免太慢）
MAX_ANALYZE_COUNT = 20

# 是否打印详细日志
VERBOSE = True
# ==================================================


def log(msg: str):
    """打印日志"""
    if VERBOSE:
        print(msg)


def get_low_price_stocks() -> pd.DataFrame:
    """
    获取15元以下的股票列表
    并进行初步筛选
    """
    log("=" * 80)
    log("步骤1: 获取A股实时行情...")
    log("=" * 80)

    try:
        # 获取实时行情
        df = ak_enhanced.stock_zh_a_spot_em()

        if df is None or df.empty:
            print("❌ 获取实时行情失败")
            return pd.DataFrame()

        log(f"✅ 成功获取 {len(df)} 只股票实时行情")

        # 列名映射（AKShare返回的列名）
        # 常见列名：'代码', '名称', '最新价', '涨跌幅', '涨跌额', '成交量', '成交额', '振幅', '最高', '最低', '今开', '昨收'

        # 筛选条件
        conditions = (
            (df['最新价'] >= MIN_PRICE) &  # 高于最低价
            (df['最新价'] <= MAX_PRICE) &  # 低于最高价
            (df['涨跌幅'] >= MIN_CHANGE_PCT) &  # 今日上涨
            (df['涨跌幅'] <= MAX_CHANGE_PCT) &  # 但未暴涨
            (df['成交额'] >= MIN_AMOUNT * 100000000)  # 成交额大于阈值（转换为元）
        )

        filtered_df = df[conditions].copy()

        log(f"✅ 筛选后剩余 {len(filtered_df)} 只股票")

        # 按成交额排序（流动性好的优先）
        filtered_df = filtered_df.sort_values(by='成交额', ascending=False)

        return filtered_df

    except Exception as e:
        print(f"❌ 筛选股票失败: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


def quick_technical_analysis(symbol: str, name: str) -> Dict[str, Any]:
    """
    快速技术分析（只分析关键指标）
    用于批量筛选
    """
    try:
        # 创建分析器
        analyzer = TechnicalAnalyzer()

        # 获取实时行情
        realtime = analyzer.get_realtime_quotes(symbol)

        if not realtime:
            return None

        # 获取K线数据（只获取最近30天，加快速度）
        kline_data = analyzer.get_kline_data(symbol, frequency='daily', offset=30)

        if kline_data is None or kline_data.empty:
            return None

        # 计算简单技术指标
        latest = kline_data.iloc[-1]
        prev = kline_data.iloc[-2] if len(kline_data) > 1 else latest

        # 价格位置（相对于近期高点/低点）
        recent_high = kline_data['high'].tail(20).max()
        recent_low = kline_data['low'].tail(20).min()
        current_price = realtime['price']
        price_position = (current_price - recent_low) / (recent_high - recent_low) * 100 if recent_high != recent_low else 50

        # 均线趋势
        ma5 = kline_data['close'].tail(5).mean()
        ma20 = kline_data['close'].tail(20).mean()

        # 成交量趋势
        vol_ma5 = kline_data['volume'].tail(5).mean() if 'volume' in kline_data.columns else 0
        latest_vol = realtime.get('volume', 0)
        volume_ratio = latest_vol / vol_ma5 if vol_ma5 > 0 else 1

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

        # 4. 涨幅（温和上涨最好，0-20分）
        change_pct = realtime.get('change_pct', 0)
        if 2 < change_pct < 5:
            score += 20
        elif 0 < change_pct <= 2:
            score += 15
        elif 5 <= change_pct < 8:
            score += 10

        result = {
            'symbol': symbol,
            'name': name,
            'price': current_price,
            'change_pct': change_pct,
            'price_position': round(price_position, 2),
            'ma5': round(ma5, 2),
            'ma20': round(ma20, 2),
            'volume_ratio': round(volume_ratio, 2),
            'score': score,
            'source': realtime.get('source', 'unknown')
        }

        return result

    except Exception as e:
        log(f"⚠️ 分析 {symbol}({name}) 失败: {e}")
        return None


def batch_analyze_stocks(stocks_df: pd.DataFrame, max_count: int = MAX_ANALYZE_COUNT) -> List[Dict[str, Any]]:
    """
    批量分析股票
    """
    log("=" * 80)
    log(f"步骤2: 批量技术分析（最多分析 {max_count} 只）...")
    log("=" * 80)

    results = []
    count = 0

    for idx, row in stocks_df.iterrows():
        if count >= max_count:
            break

        symbol = row['代码']
        name = row['名称']

        log(f"\n正在分析 {count + 1}/{max_count}: {symbol}({name})...")

        result = quick_technical_analysis(symbol, name)

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
    log("步骤3: 生成分析报告...")
    log("=" * 80)

    if not results:
        return "❌ 没有找到符合条件的股票"

    # 按得分排序
    sorted_results = sorted(results, key=lambda x: x['score'], reverse=True)

    # 生成Markdown报告
    report = f"""# 15元以下具有上涨空间的股票推荐

## 筛选条件
- 股价: {MIN_PRICE}元 ~ {MAX_PRICE}元
- 今日涨幅: {MIN_CHANGE_PCT}% ~ {MAX_CHANGE_PCT}%
- 成交额: ≥ {MIN_AMOUNT}亿元
- 分析数量: {len(results)} 只

## 推荐股票（按得分排序）

"""

    for i, stock in enumerate(sorted_results, 1):
        report += f"""
### {i}. {stock['name']}({stock['symbol']})

- **当前价格**: {stock['price']:.2f} 元
- **今日涨幅**: {stock['change_pct']:.2f}%
- **技术得分**: {stock['score']}/100
- **价格位置**: {stock['price_position']:.1f}% （近期区间）
- **均线**: MA5={stock['ma5']:.2f}, MA20={stock['ma20']:.2f}
- **量比**: {stock['volume_ratio']:.2f}
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

        report += "\n---\n"

    # 总结
    report += f"""
## 投资建议

1. **优先关注前3只股票**，技术面得分最高
2. **结合基本面分析**，技术面只是参考
3. **控制仓位**，分批买入
4. **设置止损**，避免大幅亏损

---
*报告生成时间: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}*
*数据来源: AKShare + 东方财富API*
"""

    return report


def main():
    """主函数"""
    print("=" * 80)
    print("15元以下具有上涨空间的股票筛选系统")
    print("=" * 80)
    print("\n配置:")
    print(f"  最高股价: {MAX_PRICE}元")
    print(f"  最低股价: {MIN_PRICE}元")
    print(f"  最低涨幅: {MIN_CHANGE_PCT}%")
    print(f"  最高涨幅: {MAX_CHANGE_PCT}%")
    print(f"  最小成交额: {MIN_AMOUNT}亿元")
    print(f"  最大分析数量: {MAX_ANALYZE_COUNT}只")
    print("\n" + "=" * 80)

    # 步骤1: 获取并筛选股票
    stocks_df = get_low_price_stocks()

    if stocks_df.empty:
        print("\n❌ 没有找到符合条件的股票")
        return

    print(f"\n✅ 找到 {len(stocks_df)} 只符合条件的股票")
    print("\n前10只股票:")
    print(stocks_df[['代码', '名称', '最新价', '涨跌幅', '成交额']].head(10).to_string())

    # 步骤2: 批量技术分析
    results = batch_analyze_stocks(stocks_df, max_count=MAX_ANALYZE_COUNT)

    if not results:
        print("\n❌ 技术分析失败，没有有效结果")
        return

    # 步骤3: 生成报告
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
