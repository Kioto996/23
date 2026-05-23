#!/usr/bin/env python3
"""
完整精准数据源方案 - 自动化填充Obsidian笔记
结合多个已验证可用的数据源
"""

import akshare as ak
import requests
import pandas as pd
import os
import time
from datetime import datetime

# 配置
OBSIDIAN_DIR = r"V:\psy\psy\stock"
CACHE_DIR = r"D:\workbuddy's dates\2026-05-12-task-2\cache"
os.makedirs(CACHE_DIR, exist_ok=True)

def fetch_limit_up_data(date_str=None):
    """获取涨停板数据 - AkShare（已验证可用）"""
    if date_str is None:
        date_str = datetime.now().strftime("%Y%m%d")

    print(f"📊 获取涨停板数据: {date_str}...")

    try:
        df = ak.stock_zt_pool_em(date=date_str)
        if df is not None and not df.empty:
            print(f"✅ 成功获取 {len(df)} 只涨停股")
            return df
    except Exception as e:
        print(f"❌ 获取失败: {e}")
        return None

def fetch_realtime_price(stock_code):
    """获取实时行情 - 腾讯API（已验证可用）"""
    try:
        # 标准化代码
        if len(stock_code) == 6:
            market = 'sh' if stock_code.startswith('6') else 'sz'
            full_code = f"{market}{stock_code}"
        else:
            full_code = stock_code

        url = f"http://qt.gtimg.cn/q={full_code}"
        resp = requests.get(url, timeout=10)

        if resp.status_code == 200:
            parts = resp.text.split('~')
            if len(parts) >= 33:
                return {
                    'code': stock_code,
                    'name': parts[1] if len(parts) > 1 else 'N/A',
                    'price': float(parts[3]) if parts[3] else 0,
                    'change_pct': float(parts[32]) if len(parts) > 32 and parts[32] else 0,
                    'high': float(parts[33]) if len(parts) > 33 and parts[33] else 0,
                    'low': float(parts[34]) if len(parts) > 34 and parts[34] else 0,
                    'amount': float(parts[36]) if len(parts) > 36 and parts[36] else 0,
                    'turn_over': float(parts[38]) if len(parts) > 38 and parts[38] else 0
                }
    except Exception as e:
        print(f"⚠️ 获取{stock_code}实时行情失败: {e}")
        return None

def generate_daily_observation(df, date_str):
    """生成每日观察Markdown（填充到5月.md）"""
    if df is None or df.empty:
        return f"## {date_str} 涨停板分析\n\n数据获取失败\n"

    markdown = f"## {date_str} 涨停板分析\n\n"
    markdown += f"**总计**: {len(df)} 只涨停股 | "
    markdown += f"**连板最高**: {df['连板数'].max()}板 | "
    markdown += f"**数据来源**: AkShare (已验证)\n\n"

    # 连板梯队
    markdown += f"### 连板梯队\n\n"
    for board_num in sorted(df['连板数'].unique(), reverse=True):
        board_stocks = df[df['连板数'] == board_num]
        if board_num >= 2:
            markdown += f"**{board_num}板** ({len(board_stocks)}只): "
        else:
            markdown += f"**1板** ({len(board_stocks)}只): "

        stock_links = [f"[[个股/{row['名称']}]]" for _, row in board_stocks.head(5).iterrows()]
        markdown += "、".join(stock_links)
        if len(board_stocks) > 5:
            markdown += f" 等{len(board_stocks)}只"
        markdown += "\n"

    # 行业分布
    if '所属行业' in df.columns:
        markdown += f"\n### 行业分布\n\n"
        industry_counts = df['所属行业'].value_counts().head(10)
        for industry, count in industry_counts.items():
            markdown += f"- **{industry}**: {count}只\n"

    # 封板资金最强
    if '封板资金' in df.columns:
        markdown += f"\n### 封板资金最强（前5）\n\n"
        markdown += f"| 股票 | 代码 | 连板 | 封板资金 | 所属行业 |\n"
        markdown += f"|------|------|------|---------|----------|\n"

        top5 = df.nlargest(5, '封板资金')
        for _, row in top5.iterrows():
            fd_money = row['封板资金']
            fd_str = f"{fd_money/1e8:.2f}亿" if fd_money >= 1e8 else f"{fd_money/1e4:.2f}万"
            markdown += f"| [[个股/{row['名称']}]] | {row['代码']} | {row['连板数']}板 | {fd_str} | {row.get('所属行业', 'N/A')} |\n"

    return markdown

def update_stock_pages(df):
    """批量更新个股页面"""
    print(f"\n开始批量更新个股页面...")

    success_count = 0
    for _, row in df.iterrows():
        stock_code = str(row['代码'])
        stock_name = row['名称']

        # 获取实时行情
        realtime = fetch_realtime_price(stock_code)

        # 生成Markdown
        markdown = f"---\ntitle: {stock_name}分析\ndate: {datetime.now().strftime('%Y-%m-%d %H:%M')}\ntags: [个股, 观察池]\n---\n\n"
        markdown += f"# {stock_name} ({stock_code})\n\n"

        # 涨停信息
        markdown += f"## 📊 涨停信息 ({datetime.now().strftime('%Y-%m-%d %H:%M')})\n\n"
        markdown += f"| 项目 | 数值 |\n|------|------|\n"
        markdown += f"| 最新价 | ¥{row['最新价']:.2f} |\n"
        markdown += f"| 涨跌幅 | {row['涨跌幅']:.2f}% |\n"
        markdown += f"| 连板数 | {row['连板数']}板 |\n"

        if '封板资金' in row:
            fd_money = row['封板资金']
            fd_str = f"{fd_money/1e8:.2f}亿" if fd_money >= 1e8 else f"{fd_money/1e4:.2f}万"
            markdown += f"| 封板资金 | {fd_str} |\n"

        if '首次封板时间' in row and row['首次封板时间']:
            markdown += f"| 首次封板 | {row['首次封板时间']} |\n"

        # 实时行情（如果有）
        if realtime:
            markdown += f"\n## 💹 实时行情\n\n"
            markdown += f"| 项目 | 数值 |\n|------|------|\n"
            markdown += f"| 最高 | ¥{realtime['high']:.2f} |\n"
            markdown += f"| 最低 | ¥{realtime['low']:.2f} |\n"
            amount_str = f"{realtime['amount']/1e8:.2f}亿" if realtime['amount'] >= 1e8 else f"{realtime['amount']/1e4:.2f}万"
            markdown += f"| 成交额 | {amount_str} |\n"
            markdown += f"| 换手率 | {realtime['turn_over']:.2f}% |\n"

        # 板块链接
        markdown += f"\n## 🔗 板块链接\n\n"
        if '所属行业' in row:
            markdown += f"- 所属板块: [[板块个股分析#{row['所属行业']}]]\n"
        markdown += f"- 返回每日观察: [[5月#{datetime.now().strftime('%Y-%m-%d')}]]\n\n"

        # 操作记录
        markdown += f"## 📝 操作记录\n\n"
        markdown += f"| 日期 | 操作 | 价格 | 理由 | 板块状态 |\n"
        markdown += f"|------|------|------|------|----------|\n"

        price_str = f"¥{realtime['price']:.2f}" if realtime else f"¥{row['最新价']:.2f}"
        reason = f"连板{row['连板数']}"
        if '封板资金' in row:
            fd_money = row['封板资金']
            fd_str = f"{fd_money/1e8:.2f}亿" if fd_money >= 1e8 else f"{fd_money/1e4:.2f}万"
            reason += f"，封板{fd_str}"

        markdown += f"| {datetime.now().strftime('%Y-%m-%d')} | 观察 | {price_str} | {reason} | 待分析 |\n\n"

        # 买入/卖出检查清单
        markdown += f"## ✅ 买入/卖出检查清单\n\n"
        markdown += f"### 买入信号\n"
        markdown += f"- [ ] 板块处于阶段1-2（启动/确认）\n"
        markdown += f"- [ ] 是个股龙头或前3强\n"
        markdown += f"- [ ] 价格 ≤ MA20 ±5%\n"
        markdown += f"- [ ] 封板资金 > 5000万（涨停股）\n\n"

        markdown += f"### 卖出信号\n"
        markdown += f"- [ ] 板块进入阶段4-5（高位震荡/衰退）\n"
        markdown += f"- [ ] 个股跌破MA20\n"
        markdown += f"- [ ] 封板资金 < 1000万（涨停股）\n\n"

        # 写入文件
        file_path = os.path.join(OBSIDIAN_DIR, "个股", f"{stock_name}.md")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(markdown)

        print(f"✅ 已更新: {stock_name}")
        success_count += 1

        time.sleep(0.2)  # 避免请求过快

    print(f"\n✅ 完成！成功更新 {success_count}/{len(df)} 只股票")
    return success_count

def main():
    """主函数"""
    print("=" * 60)
    print("完整精准数据源方案 - 自动化填充Obsidian")
    print("=" * 60)

    # 1. 获取涨停板数据
    date_str = datetime.now().strftime("%Y%m%d")
    df = fetch_limit_up_data(date_str)

    if df is None:
        print("\n❌ 无法获取涨停板数据")
        return

    # 2. 保存原始数据
    cache_file = os.path.join(CACHE_DIR, f"涨停板_{date_str}.csv")
    df.to_csv(cache_file, index=False, encoding='utf-8-sig')
    print(f"✅ 数据已缓存: {cache_file}")

    # 3. 生成每日观察Markdown
    markdown = generate_daily_observation(df, date_str.replace('%Y%m%d', '%Y-%m-%d'))
    obsidian_file = os.path.join(OBSIDIAN_DIR, "..", "cache", f"每日观察_{date_str}.md")
    os.makedirs(os.path.dirname(obsidian_file), exist_ok=True)
    with open(obsidian_file, 'w', encoding='utf-8') as f:
        f.write(markdown)
    print(f"✅ 每日观察已生成: {obsidian_file}")

    # 4. 批量更新个股页面
    update_stock_pages(df)

    print("\n" + "=" * 60)
    print("✅ 所有数据已填充到Obsidian笔记！")
    print("=" * 60)
    print("\n💡 下一步:")
    print("1. 打开Obsidian，查看更新的笔记")
    print("2. 如需个股基本面数据（PE、PB等），请修复AkShare源码")
    print("3. 或注册Tushare获取专业级数据")

if __name__ == "__main__":
    main()
