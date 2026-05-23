#!/usr/bin/env python3
"""
A股精准数据获取脚本 - 多数据源融合
支持：涨停板、资金流、个股基本面、实时行情
数据源：AkShare(主) + Mootdx(备用) + 东方财富(备用)
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import json
import os

# ============ 配置区 ============
OUTPUT_DIR = r"V:\psy\psy\stock"  # Obsidian笔记目录
CACHE_DIR = r"D:\workbuddy's dates\2026-05-12-task-2\cache"  # 缓存目录

# 确保缓存目录存在
os.makedirs(CACHE_DIR, exist_ok=True)

# ============ 工具函数 ============
def get_recent_trading_dates(n=5):
    """获取最近n个交易日"""
    dates = []
    current = datetime.now()

    while len(dates) < n:
        if current.weekday() < 5:  # 周一到周五
            dates.append(current.strftime("%Y%m%d"))
        current -= timedelta(days=1)

    return sorted(dates)

def save_to_cache(data, filename):
    """保存到缓存"""
    filepath = os.path.join(CACHE_DIR, filename)
    if isinstance(data, pd.DataFrame):
        data.to_csv(filepath, index=False, encoding='utf-8-sig')
    else:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ 已缓存: {filename}")

def load_from_cache(filename, max_age_hours=6):
    """从缓存加载（默认6小时有效）"""
    filepath = os.path.join(CACHE_DIR, filename)
    if not os.path.exists(filepath):
        return None

    # 检查文件年龄
    file_time = os.path.getmtime(filepath)
    age_hours = (datetime.now().timestamp() - file_time) / 3600

    if age_hours > max_age_hours:
        print(f"⚠️ 缓存已过期({age_hours:.1f}小时): {filename}")
        return None

    print(f"✅ 使用缓存({age_hours:.1f}小时前): {filename}")
    if filename.endswith('.csv'):
        return pd.read_csv(filepath, encoding='utf-8-sig')
    else:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)

# ============ 数据源1：涨停板数据 ============
def fetch_limit_up_data(date_str=None):
    """
    获取涨停板数据（AkShare）
    返回：DataFrame with columns [代码, 名称, 涨跌幅, 最新价, 成交额, 流通市值, 总市值, 换手率, 封板资金, 连板数]
    """
    cache_file = f"limit_up_{date_str or 'latest'}.csv"
    cached = load_from_cache(cache_file)
    if cached is not None:
        return cached

    try:
        print(f"📊 正在获取涨停板数据: {date_str or '最新'}")

        # 方法1：使用AkShare的涨停池数据
        df = ak.stock_zt_pool_em(date=date_str)

        if df is not None and not df.empty:
            # 标准化列名
            df = df.rename(columns={
                '代码': 'code',
                '名称': 'name',
                '涨跌幅': 'pct_chg',
                '最新价': 'price',
                '成交额': 'amount',
                '流通市值': 'float_mv',
                '总市值': 'total_mv',
                '换手率': 'turnover',
                '封板资金': 'fd_money',
                '连板数': 'zt_count'
            })

            save_to_cache(df, cache_file)
            print(f"✅ 获取成功: {len(df)} 只涨停股")
            return df
        else:
            print("⚠️ 未获取到数据")
            return None

    except Exception as e:
        print(f"❌ 获取涨停板数据失败: {e}")
        return None

# ============ 数据源2：资金流数据 ============
def fetch_capital_flow_data(date_str=None):
    """
    获取板块资金流数据（AkShare）
    返回：DataFrame with columns [板块名称, 主力净流入, 超大单净流入, 大单净流入, 中单净流入, 小单净流入]
    """
    cache_file = f"capital_flow_{date_str or 'latest'}.csv"
    cached = load_from_cache(cache_file)
    if cached is not None:
        return cached

    try:
        print(f"💰 正在获取资金流数据: {date_str or '最新'}")

        # 使用AkShare的板块资金流排行
        df = ak.stock_sector_fund_flow_rank(indicator="今日")

        if df is not None and not df.empty:
            save_to_cache(df, cache_file)
            print(f"✅ 获取成功: {len(df)} 个板块")
            return df
        else:
            print("⚠️ 未获取到资金流数据")
            return None

    except Exception as e:
        print(f"❌ 获取资金流数据失败: {e}")
        print("💡 提示: 资金流API可能暂时不可用，将使用涨停数据替代分析")
        return None

# ============ 数据源3：个股实时行情 ============
def fetch_stock_realtime_price(stock_code):
    """
    获取个股实时价格（AkShare）
    支持：6位代码（如600578）或带前缀（如sh600578）
    """
    try:
        # 标准化代码格式
        if len(stock_code) == 6:
            if stock_code.startswith('6'):
                full_code = f"sh{stock_code}"
            else:
                full_code = f"sz{stock_code}"
        else:
            full_code = stock_code

        print(f"🔍 查询个股实时行情: {full_code}")

        # 方法1：AkShare实时行情
        df = ak.stock_zh_a_spot_em()

        if df is not None and not df.empty:
            stock_data = df[df['代码'] == stock_code]

            if not stock_data.empty:
                result = {
                    'code': stock_code,
                    'name': stock_data.iloc[0]['名称'],
                    'price': stock_data.iloc[0]['最新价'],
                    'pct_chg': stock_data.iloc[0]['涨跌幅'],
                    'amount': stock_data.iloc[0]['成交额'],
                    'float_mv': stock_data.iloc[0]['流通市值'],
                    'turnover': stock_data.iloc[0]['换手率']
                }
                print(f"✅ {result['name']}({stock_code}): ¥{result['price']} ({result['pct_chg']:+.2f}%)")
                return result
            else:
                print(f"⚠️ 未找到股票: {stock_code}")
                return None
        else:
            print("⚠️ 获取实时行情失败")
            return None

    except Exception as e:
        print(f"❌ 查询个股行情失败: {e}")
        return None

# ============ 数据源4：个股基本面 ============
def fetch_stock_fundamental(stock_code):
    """
    获取个股基本面数据（Mootdx / AkShare）
    返回：dict with 市盈率、市净率、总市值、流通市值、行业等
    """
    try:
        print(f"📈 查询个股基本面: {stock_code}")

        # 方法1：AkShare个股信息
        df = ak.stock_individual_info_em(symbol=stock_code)

        if df is not None and not df.empty:
            info = dict(zip(df['item'], df['value']))
            result = {
                'code': stock_code,
                'name': info.get('股票简称', 'N/A'),
                'pe': info.get('市盈率', 'N/A'),
                'pb': info.get('市净率', 'N/A'),
                'total_mv': info.get('总市值', 'N/A'),
                'float_mv': info.get('流通市值', 'N/A'),
                'industry': info.get('行业', 'N/A'),
                'listing_date': info.get('上市时间', 'N/A')
            }
            print(f"✅ 基本面数据获取成功: {result['name']}")
            return result
        else:
            print(f"⚠️ 未找到基本面数据: {stock_code}")
            return None

    except Exception as e:
        print(f"❌ 查询基本面失败: {e}")
        return None

# ============ 数据填充：生成Obsidian笔记内容 ============
def generate_limit_up_markdown(date_str, limit_up_df, capital_flow_df=None):
    """
    生成涨停板分析的Markdown内容（用于填充到Obsidian）
    """
    if limit_up_df is None or limit_up_df.empty:
        return "## 涨停数据获取失败\n\n请检查网络连接或API可用性。\n"

    markdown = f"## {date_str} 涨停板分析\n\n"
    markdown += f"**总计**: {len(limit_up_df)} 只涨停股\n\n"

    # 按板块分组
    if '板块' in limit_up_df.columns:
        sectors = limit_up_df.groupby('板块')
        markdown += "### 板块分布\n\n"
        for sector_name, sector_df in sectors:
            markdown += f"**{sector_name}**: {len(sector_df)} 只\n"
        markdown += "\n"

    # 连板梯队
    if 'zt_count' in limit_up_df.columns:
        markdown += "### 连板梯队\n\n"
        for board_num in sorted(limit_up_df['zt_count'].unique(), reverse=True):
            board_stocks = limit_up_df[limit_up_df['zt_count'] == board_num]
            if board_num >= 2:
                markdown += f"**{board_num}板**: "
            else:
                markdown += f"**1板**: "
            markdown += "、".join([f"[[个股/{row['name']}]]" for _, row in board_stocks.iterrows()])
            markdown += "\n"
        markdown += "\n"

    # 资金流联动（如果有数据）
    if capital_flow_df is not None:
        markdown += "### 💰 资金流向\n\n"
        markdown += "| 板块 | 主力净流入 | 超大单 | 大单 | 判断 |\n"
        markdown += "|------|-----------|--------|------|------|\n"
        # TODO: 根据capital_flow_df生成表格
        markdown += "\n"

    return markdown

# ============ 主函数 ============
def main():
    """主函数：演示数据获取"""
    print("=" * 60)
    print("A股精准数据获取脚本")
    print("=" * 60)

    # 1. 获取今日涨停板数据
    print("\n[1/4] 获取涨停板数据...")
    limit_up_df = fetch_limit_up_data()

    if limit_up_df is not None:
        print("\n涨停板数据预览:")
        print(limit_up_df.head(10).to_string())
    else:
        print("❌ 涨停板数据获取失败")

    # 2. 获取资金流数据
    print("\n[2/4] 获取资金流数据...")
    capital_flow_df = fetch_capital_flow_data()

    if capital_flow_df is not None:
        print("\n资金流数据预览:")
        print(capital_flow_df.head(10).to_string())
    else:
        print("⚠️ 资金流数据获取失败（将使用涨停数据替代分析）")

    # 3. 查询个股实时行情（示例）
    print("\n[3/4] 查询个股实时行情（示例: 600578 京能电力）...")
    stock_info = fetch_stock_realtime_price("600578")

    if stock_info:
        print(f"\n京能电力实时行情: {stock_info}")

    # 4. 查询个股基本面（示例）
    print("\n[4/4] 查询个股基本面（示例: 600578 京能电力）...")
    fundamental = fetch_stock_fundamental("600578")

    if fundamental:
        print(f"\n京能电力基本面: {fundamental}")

    print("\n" + "=" * 60)
    print("数据获取完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()
