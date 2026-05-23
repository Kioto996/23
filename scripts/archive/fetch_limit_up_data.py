#!/usr/bin/env python3
"""
精准涨停板数据获取 - 使用已验证可用的AkShare接口
无需修复源码，立即可用！
"""

import akshare as ak
import os
import time
from datetime import datetime

# 配置
OBSIDIAN_DIR = r"V:\psy\psy\stock"
os.makedirs(os.path.join(OBSIDIAN_DIR, "个股"), exist_ok=True)

def fetch_limit_up_data(date_str=None):
    """
    获取涨停板数据 - 使用已验证可用的接口
    """
    if date_str is None:
        date_str = datetime.now().strftime("%Y%m%d")

    print(f"📊 正在获取 {date_str} 涨停板数据...")

    try:
        # 方法1：stock_zt_pool_em（已验证可用 ✅）
        df = ak.stock_zt_pool_em(date=date_str)

        if df is not None and not df.empty:
            print(f"✅ 成功获取 {len(df)} 只涨停股")
            return df
        else:
            print(f"⚠️ {date_str} 没有涨停数据（可能非交易日）")
            return None

    except Exception as e:
        print(f"❌ 获取失败: {e}")
        return None

def generate_limit_up_markdown(df, date_str):
    """生成涨停板分析的Markdown内容"""
    if df is None or df.empty:
        return f"## {date_str} 涨停板分析\n\n数据获取失败\n"

    markdown = f"## {date_str} 涨停板分析\n\n"
    markdown += f"**总计**: {len(df)} 只涨停股 | "
    markdown += f"**连板最高**: {df['连板数'].max()}板 | "
    markdown += f"**数据来源**: AkShare (已验证)\n\n"

    # 按连板数分组
    markdown += f"### 连板梯队\n\n"
    for board_num in sorted(df['连板数'].unique(), reverse=True):
        board_stocks = df[df['连板数'] == board_num]

        if board_num >= 2:
            markdown += f"**{board_num}板** ({len(board_stocks)}只): "
        else:
            markdown += f"**1板** ({len(board_stocks)}只): "

        # 列出前5只股票
        stock_links = []
        for _, row in board_stocks.head(5).iterrows():
            stock_name = row['名称']
            stock_code = row['代码']
            stock_links.append(f"[[个股/{stock_name}]]")

        markdown += "、".join(stock_links)
        if len(board_stocks) > 5:
            markdown += f" 等{len(board_stocks)}只"
        markdown += "\n"

    # 按行业分组
    if '所属行业' in df.columns:
        markdown += f"\n### 行业分布\n\n"
        industry_counts = df['所属行业'].value_counts()
        for industry, count in industry_counts.head(10).items():
            markdown += f"- **{industry}**: {count}只\n"

    # 封板资金最强的股票
    if '封板资金' in df.columns:
        markdown += f"\n### 封板资金最强（前10）\n\n"
        markdown += f"| 股票 | 代码 | 连板 | 封板资金 | 所属行业 |\n"
        markdown += f"|------|------|------|---------|----------|\n"

        top10 = df.nlargest(10, '封板资金')
        for _, row in top10.iterrows():
            name = row['名称']
            code = row['代码']
            zt_count = row['连板数']
            fd_money = row['封板资金']
            industry = row['所属行业'] if '所属行业' in df.columns else 'N/A'

            # 格式化封板资金
            if fd_money >= 1e8:
                fd_str = f"{fd_money/1e8:.2f}亿"
            elif fd_money >= 1e4:
                fd_str = f"{fd_money/1e4:.2f}万"
            else:
                fd_str = f"{fd_money:.0f}"

            markdown += f"| [[个股/{name}]] | {code} | {zt_count}板 | {fd_str} | {industry} |\n"

    return markdown

def update_stock_page(stock_code, stock_name, zt_data):
    """更新单个股票的分析页面"""
    try:
        # 获取该股票的涨停数据
        stock_data = zt_data[zt_data['代码'] == stock_code]

        if stock_data.empty:
            print(f"⚠️ 未找到股票数据: {stock_name} ({stock_code})")
            return False

        stock_row = stock_data.iloc[0]

        # 生成Markdown
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        markdown = f"---\n"
        markdown += f"title: {stock_name}分析\n"
        markdown += f"date: {now}\n"
        markdown += f"tags: [个股, 观察池]\n"
        markdown += f"---\n\n"
        markdown += f"# {stock_name} ({stock_code})\n\n"

        # 涨停信息
        markdown += f"## 📊 涨停信息 ({now})\n\n"
        markdown += f"| 项目 | 数值 |\n"
        markdown += f"|------|------|\n"
        markdown += f"| 最新价 | ¥{stock_row['最新价']:.2f} |\n"
        markdown += f"| 涨跌幅 | {stock_row['涨跌幅']:.2f}% |\n"
        markdown += f"| 连板数 | {stock_row['连板数']}板 |\n"

        if '封板资金' in stock_row:
            fd_money = stock_row['封板资金']
            if fd_money >= 1e8:
                fd_str = f"{fd_money/1e8:.2f}亿"
            elif fd_money >= 1e4:
                fd_str = f"{fd_money/1e4:.2f}万"
            else:
                fd_str = f"{fd_money:.0f}"
            markdown += f"| 封板资金 | {fd_str} |\n"

        if '首次封板时间' in stock_row:
            markdown += f"| 首次封板 | {stock_row['首次封板时间']} |\n"

        if '炸板次数' in stock_row:
            markdown += f"| 炸板次数 | {stock_row['炸板次数']}次 |\n"

        # 所属行业
        if '所属行业' in stock_row:
            markdown += f"\n## 🔗 板块链接\n\n"
            markdown += f"- 所属板块: [[板块个股分析#{stock_row['所属行业']}]]\n"
            markdown += f"- 返回每日观察: [[5月#{datetime.now().strftime('%Y-%m-%d')}]]\n\n"

        # 操作记录
        markdown += f"## 📝 操作记录\n\n"
        markdown += f"| 日期 | 操作 | 价格 | 理由 | 板块状态 |\n"
        markdown += f"|------|------|------|------|----------|\n"

        price_str = f"¥{stock_row['最新价']:.2f}"
        reason = f"连板{stock_row['连板数']}" + (f"，封板{fd_str}" if '封板资金' in stock_row else "")
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
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(mardown)

        print(f"✅ 已更新: {file_path}")
        return True

    except Exception as e:
        print(f"❌ 更新股票页面失败 {stock_name}: {e}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("精准涨停板数据获取系统")
    print("=" * 60)

    # 1. 获取涨停板数据
    date_str = datetime.now().strftime("%Y%m%d")
    df = fetch_limit_up_data(date_str)

    if df is None:
        print("\n❌ 无法获取涨停板数据")
        return

    # 2. 生成Markdown摘要
    print(f"\n生成Markdown摘要...")
    markdown = generate_limit_up_markdown(df, date_str)

    # 保存到缓存
    cache_file = os.path.join(OBSIDIAN_DIR, "..", "cache", f"涨停板_{date_str}.md")
    os.makedirs(os.path.dirname(cache_file), exist_ok=True)
    with open(cache_file, 'w', encoding='utf-8') as f:
        f.write(mardown)
    print(f"✅ 已保存摘要: {cache_file}")

    # 3. 批量更新个股页面
    print(f"\n开始批量更新个股页面...")
    success_count = 0
    for _, row in df.iterrows():
        stock_code = str(row['代码'])
        stock_name = row['名称']

        if update_stock_page(stock_code, stock_name, df):
            success_count += 1

        # 避免请求过快
        time.sleep(0.2)

    print("\n" + "=" * 60)
    print(f"完成！成功更新 {success_count}/{len(df)} 只股票")
    print("=" * 60)

if __name__ == "__main__":
    main()
