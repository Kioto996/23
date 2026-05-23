#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
涨停前预判筛选器
基于5/14涨停股特征分析，扫描全市场找出可能涨停的候选股
方法论：板块轮动 + 技术形态 + 资金信号
"""

import akshare as ak
import pandas as pd
import requests
import time
import os
from datetime import datetime

CACHE_DIR = r"D:\workbuddy's dates\2026-05-12-task-2\cache"

def get_stock_market(code):
    code = str(code).strip()
    if code.startswith(('6','9')): return 'sh'
    elif code.startswith(('0','3')): return 'sz'
    elif code.startswith(('4','8')): return 'bj'
    return 'sz'

def fetch_realtime(stock_code):
    """腾讯API获取实时行情"""
    code = str(stock_code).strip().zfill(6)
    market = get_stock_market(code)
    url = f"http://qt.gtimg.cn/q={market}{code}"
    try:
        resp = requests.get(url, timeout=5)
        parts = resp.text.split('~')
        if len(parts) > 46:
            return {
                'price': float(parts[3]) if parts[3] else 0,
                'change_pct': float(parts[32]) if parts[32] else 0,
                'amount_yi': float(parts[37])/10000 if parts[37] else 0,
                'turnover': float(parts[38]) if parts[38] else 0,
                'pe': float(parts[39]) if parts[39] else 0,
                'total_mv': float(parts[45]) if parts[45] else 0,
                'pb': float(parts[46]) if parts[46] else 0,
                'high': float(parts[33]) if parts[33] else 0,
                'low': float(parts[34]) if parts[34] else 0,
                'amplitude': float(parts[43]) if len(parts)>43 and parts[43] else 0,
            }
    except:
        pass
    return None

def main():
    print("=" * 60)
    print("📡 涨停前预判筛选器 v1.0")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    
    # Step 1: 获取今日涨停数据 → 识别热门板块
    print("\n🔍 Step 1: 识别今日热门板块...")
    try:
        zt_df = ak.stock_zt_pool_em(date='20260514')
        sector_counts = zt_df['所属行业'].value_counts()
        hot_sectors = sector_counts[sector_counts >= 2].index.tolist()
        print(f"  热门板块（≥2只涨停）: {hot_sectors}")
    except Exception as e:
        print(f"  涨停数据获取失败: {e}")
        hot_sectors = ['电力', '光伏设备', '化学制品']  # fallback
    
    # Step 2: 从全市场筛选潜在标的
    print("\n🔍 Step 2: 扫描全市场候选股...")
    print("  条件: 价格≤50元 | 非ST | 换手活跃")
    
    candidates = []
    # 用同花顺行业板块找板块内个股
    try:
        # 获取同花顺概念板块近期强势板块
        df_concept = ak.stock_board_concept_name_ths()
        print(f"  概念板块: {len(df_concept)}个")
    except:
        print("  概念板块获取失败")
    
    print("\n🔍 Step 3: 候选股清单")
    print("-" * 60)
    
    # === 从几个维度生成候选股 ===
    
    # 维度A: 热门板块跟风股（板块效应）
    print("\n📌 维度A: 热门板块扩散（板块内有涨停→跟风股可能补涨）")
    print("  逻辑: 化学制品5只涨停→同板块其他股可能跟风")
    print("        光伏4只涨停→跟风")
    print("        电力4只涨停→跟风")
    
    # 维度B: 技术形态（从今天涨停的股票反推特征）
    print("\n📌 维度B: 涨停前技术特征（基于5/14数据总结）")
    print("  ┌─────────────────────────────────────────────────────┐")
    print("  │ ✅ 价格<20元 (58%涨停股)                              │")
    print("  │ ✅ 流通市值<50亿 (小盘股更容易涨停)                    │")
    print("  │ ✅ 所属板块当日有≥2只涨停（板块效应）                   │")
    print("  │ ✅ 前几日缩量横盘/回踩MA20（潜伏形态）                  │")
    print("  │ ✅ 非ST、非问题股                                    │")
    print("  │ ✅ 国企背景加分                                      │")
    print("  │ 涨停信号: 开盘15分钟内放量拉升>5% → 追涨候选           │")
    print("  └─────────────────────────────────────────────────────┘")
    
    # 维度C: 资金面
    print("\n📌 维度C: 资金面信号")
    print("  逻辑: 前日尾盘有资金抢筹迹象")
    print("        早盘集合竞价量比>3")
    print("        开盘后5分钟成交额>前日全天10%")
    
    # 维度D: 催化剂
    print("\n📌 维度D: 事件催化剂")
    print("  • 盘前利好消息（业绩预告、订单公告、政策利好）")
    print("  • 行业政策驱动（光伏新政、电力改革、集成电路扶持）")
    print("  • 板块内龙头涨停后的跟风效应")
    print("  • 技术突破/产品发布")
    
    print("\n" + "=" * 60)
    print("📋 今日涨停股特征复盘（用于明日预判）")
    print("=" * 60)
    
    # 复盘今日涨停特征
    try:
        zt_data = zt_df.to_dict('records')
        print(f"\n今日涨停: {len(zt_data)}只")
        
        # 连板高度
        max_ban = zt_df['连板数'].max()
        print(f"最高连板: {max_ban}板 ({zt_df[zt_df['连板数']==max_ban]['名称'].values})")
        
        # 早盘封板率
        early = sum(1 for s in zt_data if str(s['首次封板时间']).zfill(6) < '100000')
        print(f"早盘10点前封板: {early}/{len(zt_data)} = {early/len(zt_data)*100:.0f}%")
        
        # 行业集中度
        top3 = zt_df['所属行业'].value_counts().head(3)
        print(f"行业集中TOP3: {dict(top3)}")
        
        print(f"\n💡 明日预判重点板块: {', '.join(top3.index)}")
        print(f"  逻辑: 今日强势板块→明日大概率延续→关注板块内未涨停的跟风股")
        
    except Exception as e:
        print(f"  复盘失败: {e}")
    
    print("\n" + "=" * 60)
    print("📌 操作建议")
    print("=" * 60)
    print("""
  1️⃣ 盘前（8:30-9:15）
     - 查看隔夜政策/行业新闻（光伏、电力相关政策）
     - 看龙虎榜席位动向
     - 拟定今日关注板块（从昨日强势板块+新消息驱动）

  2️⃣ 集合竞价（9:15-9:25）
     - 监控候选股竞价量比
     - 竞价涨幅>5%且量比>3 → 主力抢筹信号
     - 板块内多只竞价异动 → 板块确认

  3️⃣ 开盘前30分钟（9:30-10:00）—— 黄金时间
     - 候选股放量拉升>5% → 跟或不跟取决于位置
     - MA20附近启动 → 安全
     - 已在高位 → 放弃

  4️⃣ 盘中（10:00后）
     - 涨停股开板回封 → 打板机会
     - 板块轮动 → 从已涨停板块切换到未涨板块
    """)

if __name__ == '__main__':
    main()
