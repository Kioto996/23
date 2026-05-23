#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用同花顺(THS)数据源补全涨停股基本面信息
- stock_financial_abstract_ths: 财务摘要（每股净资产、ROE、净利润等）
- 结合腾讯API实时行情
"""

import akshare as ak
import pandas as pd
import requests
import os
import json
import time
import re
from datetime import datetime

# ==== 配置 ====
CSV_PATH = r"D:\workbuddy's dates\2026-05-12-task-2\cache\涨停板_20260514.csv"
OBSIDIAN_DIR = r"V:\psy\psy\stock\个股"
CACHE_DIR = r"D:\workbuddy's dates\2026-05-12-task-2\cache"
ERROR_LOG = []

def log_error(msg):
    ERROR_LOG.append(msg)
    print(f"  ❌ {msg}")

def get_stock_market(code):
    """判断股票市场"""
    code = str(code).strip()
    if code.startswith('6') or code.startswith('9'):
        return 'sh'
    elif code.startswith('0') or code.startswith('3'):
        return 'sz'
    elif code.startswith('4'):
        return 'bj'
    elif code.startswith('8'):
        return 'bj'
    return 'sz'

def fetch_realtime_price(stock_code):
    """腾讯API获取实时行情"""
    code = str(stock_code).strip()
    market = get_stock_market(code)
    full_code = f"{market}{code}"
    url = f"http://qt.gtimg.cn/q={full_code}"
    
    try:
        resp = requests.get(url, timeout=10)
        text = resp.text
        if text and '~' in text:
            parts = text.split('~')
            return {
                'price': float(parts[3]) if parts[3] else None,
                'change_pct': float(parts[32]) if parts[32] else None,
                'amount': float(parts[37]) if len(parts) > 37 and parts[37] else None,
                'turn_over': float(parts[38]) if len(parts) > 38 and parts[38] else None,
                'high': float(parts[33]) if len(parts) > 33 and parts[33] else None,
                'low': float(parts[34]) if len(parts) > 34 and parts[34] else None,
                'open': float(parts[5]) if parts[5] else None,
                'pre_close': float(parts[4]) if parts[4] else None,
            }
    except Exception as e:
        log_error(f"腾讯API行情获取失败 {code}: {e}")
    return None

def fetch_financial_abstract(code):
    """同花顺获取财务摘要"""
    try:
        df = ak.stock_financial_abstract_ths(symbol=code, indicator='按报告期')
        if df is not None and not df.empty:
            # 取最新一期（最后一行，数据按时间正序排列）
            latest = df.iloc[-1].to_dict()
            result = {}
            
            for key in ['基本每股收益', '每股净资产', '每股资本公积金', '每股未分配利润', 
                       '每股经营现金流', '净利润', '营业总收入', '净利润同比增长率',
                       '营业总收入同比增长率', '扣非净利润', '销售净利率', '净资产收益率',
                       '净资产收益率-摊薄', '资产负债率', '流动比率', '速动比率']:
                if key in latest:
                    val = latest[key]
                    if val is not None and str(val) != 'False' and str(val) != 'nan':
                        result[key] = val
            
            result['报告期'] = latest.get('报告期', '')
            return result
    except Exception as e:
        log_error(f"同花顺财务摘要失败 {code}: {e}")
    return None

def fetch_industry_info(code):
    """获取个股行业信息"""
    try:
        # 用同花顺概念板块名称API查所属概念
        df_concept = ak.stock_board_concept_name_ths()
        # 用同花顺行业板块名称API查所属行业
        df_industry = ak.stock_board_industry_name_ths()
        return {'概念板块数': len(df_concept), '行业板块数': len(df_industry)}
    except Exception as e:
        log_error(f"板块信息获取失败: {e}")
    return None

def update_obsidian_note(stock_name, stock_code, zt_info, fundamental, realtime):
    """更新Obsidian笔记，添加基本面信息"""
    md_path = os.path.join(OBSIDIAN_DIR, f"{stock_name}.md")
    
    # 收集要更新的内容
    updates = []
    
    # 1. 涨跌幅修正（腾讯API更准确）
    if realtime and realtime.get('change_pct') is not None:
        updates.append(f"| 最新价 | ¥{realtime['price']:.2f} |")
        updates.append(f"| 涨跌幅 | {realtime['change_pct']:.2f}% |")
        if realtime.get('amount') is not None:
            amt_yi = realtime['amount'] / 10000
            updates.append(f"| 成交额 | {amt_yi:.2f}亿 |")
        if realtime.get('turn_over') is not None:
            updates.append(f"| 换手率 | {realtime['turn_over']:.2f}% |")
    
    # 2. 基本面数据（来自同花顺）
    if fundamental:
        fund_lines = []
        if '净利润' in fundamental:
            val = fundamental['净利润']
            fund_lines.append(f"| 净利润(最新) | {val} |")
        if '净利润同比增长率' in fundamental:
            val = fundamental['净利润同比增长率']
            fund_lines.append(f"| 净利润同比 | {val} |")
        if '营业总收入' in fundamental:
            val = fundamental['营业总收入']
            fund_lines.append(f"| 营业总收入 | {val} |")
        if '基本每股收益' in fundamental:
            val = fundamental['基本每股收益']
            fund_lines.append(f"| 基本每股收益 | {val} |")
        if '每股净资产' in fundamental:
            val = fundamental['每股净资产']
            fund_lines.append(f"| 每股净资产 | {val} |")
        if '净资产收益率' in fundamental:
            val = fundamental['净资产收益率']
            fund_lines.append(f"| ROE | {val} |")
        if '销售净利率' in fundamental:
            val = fundamental['销售净利率']
            fund_lines.append(f"| 销售净利率 | {val} |")
        if '资产负债率' in fundamental:
            val = fundamental['资产负债率']
            fund_lines.append(f"| 资产负债率 | {val} |")
        if '每股未分配利润' in fundamental:
            val = fundamental['每股未分配利润']
            fund_lines.append(f"| 每股未分配利润 | {val} |")
        
        if fund_lines:
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            fund_section = f"""
## 📊 基本面数据 (同花顺, {now})
| 项目 | 数值 |
|------|------|
""" + "\n".join(fund_lines)
            updates.append(fund_section)
    
    # 写入文件
    if not updates:
        print(f"  ⏭️ {stock_name} 无新数据可更新")
        return False
    
    try:
        if os.path.exists(md_path):
            with open(md_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查是否已有基本面部分，有则替换
            if '## 📊 基本面数据' in content:
                # 替换现有基本面部分
                pattern = r'## 📊 基本面数据.*?(?=\n## |\Z)'
                new_section = '\n'.join(updates)
                content = re.sub(pattern, new_section, content, flags=re.DOTALL)
            else:
                # 追加到文件末尾
                content += '\n'.join(updates)
            
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"  ✅ {stock_name} 更新成功")
            return True
        else:
            print(f"  ⚠️ {stock_name}.md 不存在，跳过")
            return False
    except Exception as e:
        log_error(f"写入文件失败 {stock_name}: {e}")
        return False

def main():
    # 读取CSV
    df = pd.read_csv(CSV_PATH, encoding='utf-8-sig')
    stocks = df.to_dict('records')
    print(f"📊 共 {len(stocks)} 只股票")
    
    successes = 0
    failures = 0
    results = []
    
    for i, stock in enumerate(stocks):
        code = str(stock['代码']).strip().zfill(6)  # 补零到6位
        name = stock['名称']
        print(f"\n[{i+1}/{len(stocks)}] {name}({code}) ...", end=' ')
        
        # 1. 获取实时行情
        realtime = fetch_realtime_price(code)
        time.sleep(0.3)
        
        # 2. 获取同花顺财务摘要
        fundamental = fetch_financial_abstract(code)
        time.sleep(1.5)  # 同花顺接口需要稍微慢一点
        
        # 3. 更新Obsidian笔记
        ok = update_obsidian_note(name, code, stock, fundamental, realtime)
        
        if ok:
            successes += 1
        else:
            failures += 1
        
        results.append({
            '代码': code,
            '名称': name,
            '基本面数据': '有' if fundamental else '无',
            '实时行情': '有' if realtime else '无'
        })
    
    # 输出汇总
    print(f"\n\n{'='*50}")
    print(f"📊 更新完成!")
    print(f"✅ 成功: {successes}")
    print(f"❌ 失败: {failures}")
    
    if ERROR_LOG:
        print(f"\n⚠️ 错误日志:")
        for e in ERROR_LOG:
            print(f"  {e}")
    
    # 保存结果CSV
    result_df = pd.DataFrame(results)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_path = os.path.join(CACHE_DIR, f'基本面数据_{timestamp}.csv')
    result_df.to_csv(result_path, index=False, encoding='utf-8-sig')
    print(f"\n📁 结果保存: {result_path}")

if __name__ == '__main__':
    main()
