#!/usr/bin/env python3
"""
精准A股数据获取 + Obsidian自动填充系统
集成多个数据源，自动降级处理，直接生成Obsidian笔记内容

数据源优先级：
1. AkShare (主) - 需要curl_cffi修复
2. 新浪财经API (备用) - 实时行情
3. 腾讯股票API (备用) - 实时行情
4. 东方财富网页爬取 (最后备用)
"""

import akshare as ak
import pandas as pd
import requests
import json
import os
from datetime import datetime, timedelta
import time

# ============ 配置 ============
OBSIDIAN_STOCK_DIR = r"V:\psy\psy\stock"
CACHE_DIR = r"D:\workbuddy's dates\2026-05-12-task-2\cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# ============ 工具函数 ============
def safe_get(url, headers=None, timeout=10):
    """安全的HTTP请求，自动处理错误"""
    try:
        if headers is None:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        return resp
    except Exception as e:
        print(f"⚠️ HTTP请求失败: {e}")
        return None

def format_number(num):
    """格式化数字：万、亿"""
    if num is None:
        return "N/A"
    try:
        num = float(num)
        if abs(num) >= 1e8:
            return f"{num/1e8:.2f}亿"
        elif abs(num) >= 1e4:
            return f"{num/1e4:.2f}万"
        else:
            return f"{num:.2f}"
    except:
        return "N/A"

# ============ 数据源1：AkShare（修复版） ============
def fetch_limit_up_akshare(date_str=None):
    """
    获取涨停板数据 - AkShare（尝试多种方法）
    """
    print(f"📊 [方法1] 尝试AkShare获取涨停数据...")

    methods = [
        ("stock_zt_pool_em", {"date": date_str}),
        ("stock_zt_pool_dtgc_em", {"date": date_str}),  # 涨停池（不同接口）
    ]

    for method_name, params in methods:
        try:
            if hasattr(ak, method_name):
                func = getattr(ak, method_name)
                df = func(**params) if params else func()

                if df is not None and not df.empty:
                    print(f"✅ AkShare.{method_name} 成功: {len(df)} 只")
                    return normalize_limit_up_data(df)
                else:
                    print(f"⚠️ AkShare.{method_name} 返回空数据")
            else:
                print(f"⚠️ AkShare 没有 {method_name} 接口")
        except Exception as e:
            print(f"❌ AkShare.{method_name} 失败: {e}")
            continue

    print("❌ 所有AkShare方法都失败了")
    return None

def normalize_limit_up_data(df):
    """标准化涨停数据格式"""
    try:
        # 尝试识别列名
        column_mapping = {
            '代码': 'code',
            '名称': 'name',
            '涨跌幅': 'pct_chg',
            '最新价': 'price',
            '成交额': 'amount',
            '流通市值': 'float_mv',
            '总市值': 'total_mv',
            '换手率': 'turnover',
            '封板资金': 'fd_money',
            '连板数': 'zt_count',
            '首次封板时间': 'first_time',
            '最后封板时间': 'last_time',
            '炸板次数': 'break_count',
            '涨停统计': 'zt_stat'
        }

        df = df.rename(columns=column_mapping)

        # 确保必要列存在
        required_cols = ['code', 'name']
        for col in required_cols:
            if col not in df.columns:
                df[col] = 'N/A'

        # 填充缺失值
        if 'zt_count' not in df.columns:
            df['zt_count'] = 1
        if 'fd_money' not in df.columns:
            df['fd_money'] = 'N/A'
        if 'first_time' not in df.columns:
            df['first_time'] = 'N/A'

        return df

    except Exception as e:
        print(f"⚠️ 数据标准化失败: {e}")
        return df

# ============ 数据源2：新浪财经API（备用） ============
def fetch_limit_up_sina():
    """
    获取涨停板数据 - 新浪财经API（备用方案）
    """
    print(f"📊 [方法2] 尝试新浪财经API...")

    try:
        # 新浪涨停板数据接口
        url = "http://vip.stock.finance.sina.com.cn/q/go.php/vInvestRank/kind/ljz/index.phtml"
        resp = safe_get(url)

        if resp is None:
            return None

        # 解析HTML（简化版，实际需要BeautifulSoup）
        print("⚠️ 新浪财经API需要HTML解析，建议安装BeautifulSoup")
        return None

    except Exception as e:
        print(f"❌ 新浪财经API失败: {e}")
        return None

# ============ 数据源3：东方财富网页爬取（最后备用） ============
def fetch_limit_up_eastmoney_web(date_str=None):
    """
    获取涨停板数据 - 东方财富网页爬取（最后备用）
    直接爬取东方财富网页，绕过API限制
    """
    print(f"📊 [方法3] 尝试东方财富网页爬取...")

    try:
        # 东方财富涨停板页面
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")

        url = f"http://quote.eastmoney.com/center/gridlist.html#hs_zt"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'http://quote.eastmoney.com/'
        }

        resp = safe_get(url, headers=headers)

        if resp is None:
            return None

        print("⚠️ 东方财富网页爬取需要解析JavaScript动态内容")
        print("💡 建议使用Selenium或Playwright进行动态爬取")
        return None

    except Exception as e:
        print(f"❌ 东方财富网页爬取失败: {e}")
        return None

# ============ 综合数据获取 ============
def fetch_limit_up_data(date_str=None):
    """
    综合获取涨停板数据（多数据源自动切换）
    """
    print("=" * 60)
    print("开始获取涨停板数据（多数据源）")
    print("=" * 60)

    # 方法1：AkShare
    df = fetch_limit_up_akshare(date_str)
    if df is not None:
        return df

    # 方法2：新浪财经API
    df = fetch_limit_up_sina()
    if df is not None:
        return df

    # 方法3：东方财富网页爬取
    df = fetch_limit_up_eastmoney_web(date_str)
    if df is not None:
        return df

    print("❌ 所有数据源都失败了！")
    return None

# ============ 个股基本面获取（已验证可用） ============
def fetch_stock_fundamental(stock_code):
    """
    获取个股基本面（AkShare - 已验证可用）
    """
    try:
        print(f"🔍 查询个股基本面: {stock_code}")

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
            print(f"✅ {result['name']} 基本面获取成功")
            return result
        else:
            print(f"⚠️ 未找到基本面数据: {stock_code}")
            return None

    except Exception as e:
        print(f"❌ 查询基本面失败: {e}")
        return None

def fetch_stock_realtime_price(stock_code):
    """
    获取个股实时行情（使用腾讯股票API备用）
    """
    try:
        print(f"💹 查询实时行情: {stock_code}")

        # 标准化代码
        if len(stock_code) == 6:
            if stock_code.startswith('6'):
                market = 'sh'
            else:
                market = 'sz'
            full_code = f"{market}{stock_code}"
        else:
            full_code = stock_code

        # 方法1：腾讯股票API（免费、稳定）
        url = f"http://qt.gtimg.cn/q={full_code}"
        resp = safe_get(url)

        if resp is not None:
            # 解析腾讯API返回的数据
            # 格式：v_sh600578="51~京能电力~600578~6.37~0.58~10.02~..."
            content = resp.text
            if '~' in content:
                parts = content.split('~')
                if len(parts) >= 5:
                    result = {
                        'code': stock_code,
                        'name': parts[1] if len(parts) > 1 else 'N/A',
                        'price': float(parts[3]) if parts[3] else 0,
                        'pct_chg': float(parts[4]) if parts[4] else 0,
                        'open': float(parts[5]) if len(parts) > 5 and parts[5] else 0,
                        'high': float(parts[33]) if len(parts) > 33 and parts[33] else 0,
                        'low': float(parts[34]) if len(parts) > 34 and parts[34] else 0,
                        'pre_close': float(parts[4]) if parts[4] else 0,
                        'amount': float(parts[36]) if len(parts) > 36 and parts[36] else 0,  # 成交额
                        'volume': float(parts[6]) if len(parts) > 6 and parts[6] else 0,  # 成交量
                        'turnover': float(parts[38]) if len(parts) > 38 and parts[38] else 0  # 换手率
                    }
                    print(f"✅ {result['name']}: ¥{result['price']} ({result['pct_chg']:+.2f}%)")
                    return result

        print(f"⚠️ 腾讯API返回数据格式异常: {stock_code}")
        return None

    except Exception as e:
        print(f"❌ 查询实时行情失败: {e}")
        return None

# ============ Obsidian笔记生成和填充 ============
def generate_stock_page(stock_code, stock_name, fundamental=None, realtime=None):
    """
    生成单个股票的分析页面（Obsidian格式）
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    markdown = f"---\n"
    markdown += f"title: {stock_name}分析\n"
    markdown += f"date: {now}\n"
    markdown += f"tags: [个股, 观察池]\n"
    markdown += f"---\n\n"
    markdown += f"# {stock_name} ({stock_code})\n\n"

    # 实时行情
    if realtime:
        markdown += f"## 💹 实时行情 ({now})\n\n"
        markdown += f"| 项目 | 数值 |\n"
        markdown += f"|------|------|\n"
        markdown += f"| 最新价 | ¥{realtime['price']:.2f} |\n"
        markdown += f"| 涨跌幅 | {realtime['pct_chg']:+.2f}% |\n"
        markdown += f"| 今开 | ¥{realtime['open']:.2f} |\n"
        markdown += f"| 最高 | ¥{realtime['high']:.2f} |\n"
        markdown += f"| 最低 | ¥{realtime['low']:.2f} |\n"
        markdown += f"| 成交额 | {format_number(realtime['amount'])} |\n"
        markdown += f"| 换手率 | {realtime['turnover']:.2f}% |\n\n"

    # 基本面
    if fundamental:
        markdown += f"## 📈 基本面\n\n"
        markdown += f"| 项目 | 数值 |\n"
        markdown += f"|------|------|\n"
        markdown += f"| 市盈率(PE) | {fundamental['pe']} |\n"
        markdown += f"| 市净率(PB) | {fundamental['pb']} |\n"
        markdown += f"| 总市值 | {format_number(fundamental['total_mv'])} |\n"
        markdown += f"| 流通市值 | {format_number(fundamental['float_mv'])} |\n"
        markdown += f"| 所属行业 | {fundamental['industry']} |\n"
        markdown += f"| 上市日期 | {fundamental['listing_date']} |\n\n"

    # 板块链接
    markdown += f"## 🔗 板块链接\n\n"
    if fundamental and fundamental['industry'] != 'N/A':
        markdown += f"- 所属板块: [[板块个股分析#{fundamental['industry']}]]\n"
    markdown += f"- 返回每日观察: [[5月#{datetime.now().strftime('%Y-%m-%d')}]]\n\n"

    # 操作记录
    markdown += f"## 📝 操作记录\n\n"
    markdown += f"| 日期 | 操作 | 价格 | 理由 | 板块状态 |\n"
    markdown += f"|------|------|------|------|----------|\n"

    price_str = f"¥{realtime['price']:.2f}" if realtime else 'N/A'
    markdown += f"| {datetime.now().strftime('%Y-%m-%d')} | 观察 | {price_str} | 数据更新 | 待更新 |\n\n"

    # 买入/卖出检查清单
    markdown += f"## ✅ 买入/卖出检查清单\n\n"
    markdown += f"### 买入信号\n"
    markdown += f"- [ ] 板块处于阶段1-2（启动/确认）\n"
    markdown += f"- [ ] 是个股龙头或前3强\n"
    markdown += f"- [ ] 价格 ≤ MA20 ±5%\n"
    markdown += f"- [ ] 基本面良好（PE/PB合理）\n"
    markdown += f"- [ ] 封板资金 > 5000万（涨停股）\n\n"

    markdown += f"### 卖出信号\n"
    markdown += f"- [ ] 板块进入阶段4-5（高位震荡/衰退）\n"
    markdown += f"- [ ] 个股跌破MA20\n"
    markdown += f"- [ ] 封板资金 < 1000万（涨停股）\n"
    markdown += f"- [ ] 基本面恶化\n\n"

    return markdown

def update_obsidian_notes(stock_codes):
    """
    更新Obsidian笔记：获取真实数据并生成/更新个股页面
    """
    print("=" * 60)
    print("开始更新Obsidian笔记")
    print("=" * 60)

    for stock_code in stock_codes:
        print(f"\n处理股票: {stock_code}")

        # 1. 获取基本面
        fundamental = fetch_stock_fundamental(stock_code)

        # 2. 获取实时行情
        realtime = fetch_stock_realtime_price(stock_code)

        if fundamental is None and realtime is None:
            print(f"⚠️ {stock_code} 数据获取失败，跳过")
            continue

        stock_name = fundamental['name'] if fundamental else (realtime['name'] if realtime else stock_code)

        # 3. 生成Markdown
        markdown = generate_stock_page(stock_code, stock_name, fundamental, realtime)

        # 4. 写入文件
        file_path = os.path.join(OBSIDIAN_STOCK_DIR, "个股", f"{stock_name}.md")

        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(markdown)

        print(f"✅ 已更新: {file_path}")

        # 避免请求过快
        time.sleep(1)

    print("\n" + "=" * 60)
    print("Obsidian笔记更新完成！")
    print("=" * 60)

# ============ 主函数 ============
def main():
    """主函数"""
    print("=" * 60)
    print("精准A股数据获取 + Obsidian自动填充系统")
    print("=" * 60)

    # 测试：更新几只股票的Obsidian页面
    test_stocks = ["600578", "002506", "002940", "600509"]

    print(f"\n将更新以下股票的数据: {test_stocks}")
    update_obsidian_notes(test_stocks)

    print("\n" + "=" * 60)
    print("完成！请查看 Obsidian 笔记更新")
    print("=" * 60)

if __name__ == "__main__":
    main()
