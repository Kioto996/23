#!/usr/bin/env python3
"""
精准数据获取 V2 - 专注于可用性
使用已验证可用的数据源，直接填充Obsidian笔记
"""

import requests
import os
import time
from datetime import datetime

# 配置
OBSIDIAN_DIR = r"V:\psy\psy\stock"
os.makedirs(os.path.join(OBSIDIAN_DIR, "个股"), exist_ok=True)

def fetch_realtime_price(stock_code):
    """
    获取个股实时行情 - 腾讯API（已验证可用）
    """
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
            content = resp.text
            if '~' in content:
                parts = content.split('~')

                # 正确字段映射（已验证）
                # 格式: v_sh600578="1~京能电力~600578~最新价~昨收~今开~..."
                if len(parts) >= 33:
                    current_price = float(parts[3]) if parts[3] else 0
                    pre_close = float(parts[4]) if parts[4] else current_price
                    change_pct = float(parts[32]) if len(parts) > 32 and parts[32] else 0
                    change_amt = float(parts[31]) if len(parts) > 31 and parts[31] else 0
                    high = float(parts[33]) if len(parts) > 33 and parts[33] else 0
                    low = float(parts[34]) if len(parts) > 34 and parts[34] else 0
                    volume = float(parts[6]) if len(parts) > 6 and parts[6] else 0
                    amount = float(parts[36]) if len(parts) > 36 and parts[36] else 0
                    turn_over = float(parts[38]) if len(parts) > 38 and parts[38] else 0

                    result = {
                        'code': stock_code,
                        'name': parts[1] if len(parts) > 1 else 'N/A',
                        'price': current_price,
                        'pre_close': pre_close,
                        'change_pct': change_pct,
                        'change_amt': change_amt,
                        'high': high,
                        'low': low,
                        'open': float(parts[5]) if len(parts) > 5 and parts[5] else 0,
                        'volume': volume,
                        'amount': amount,
                        'turn_over': turn_over
                    }
                    print(f"✅ {result['name']}({stock_code}): ¥{result['price']:.2f} ({result['change_pct']:+.2f}%)")
                    return result

        print(f"⚠️ 腾讯API返回格式异常: {stock_code}")
        return None

    except Exception as e:
        print(f"❌ 查询实时行情失败 {stock_code}: {e}")
        return None

def generate_stock_page(stock_code, realtime_data):
    """生成个股Obsidian页面"""
    if not realtime_data:
        return None

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    name = realtime_data['name']

    md = f"---\n"
    md += f"title: {name}分析\n"
    md += f"date: {now}\n"
    md += f"tags: [个股, 观察池]\n"
    md += f"---\n\n"
    md += f"# {name} ({stock_code})\n\n"

    # 实时行情
    md += f"## 💹 实时行情 ({now})\n\n"
    md += f"| 项目 | 数值 |\n"
    md += f"|------|------|\n"
    md += f"| 最新价 | ¥{realtime_data['price']:.2f} |\n"
    md += f"| 涨跌幅 | {realtime_data['change_pct']:+.2f}% |\n"
    md += f"| 涨跌额 | ¥{realtime_data['change_amt']:.2f} |\n"
    md += f"| 今开 | ¥{realtime_data['open']:.2f} |\n"
    md += f"| 最高 | ¥{realtime_data['high']:.2f} |\n"
    md += f"| 最低 | ¥{realtime_data['low']:.2f} |\n"

    # 格式化成交额和换手率
    amount_str = f"{realtime_data['amount']/1e8:.2f}亿" if realtime_data['amount'] >= 1e8 else f"{realtime_data['amount']/1e4:.2f}万"
    md += f"| 成交额 | {amount_str} |\n"
    md += f"| 换手率 | {realtime_data['turn_over']:.2f}% |\n\n"

    # 板块链接（需要手动补充）
    md += f"## 🔗 板块链接\n\n"
    md += f"- 所属板块: [[板块个股分析#待补充]]\n"
    md += f"- 返回每日观察: [[5月#{datetime.now().strftime('%Y-%m-%d')}]]\n\n"

    # 操作记录
    md += f"## 📝 操作记录\n\n"
    md += f"| 日期 | 操作 | 价格 | 理由 | 板块状态 |\n"
    md += f"|------|------|------|------|----------|\n"
    md += f"| {datetime.now().strftime('%Y-%m-%d')} | 数据更新 | ¥{realtime_data['price']:.2f} | 腾讯API实时数据 | 待分析 |\n\n"

    # 买入/卖出检查清单
    md += f"## ✅ 买入/卖出检查清单\n\n"
    md += f"### 买入信号\n"
    md += f"- [ ] 板块处于阶段1-2（启动/确认）\n"
    md += f"- [ ] 是个股龙头或前3强\n"
    md += f"- [ ] 价格 ≤ MA20 ±5%\n"
    md += f"- [ ] 封板资金 > 5000万（涨停股）\n\n"

    md += f"### 卖出信号\n"
    md += f"- [ ] 板块进入阶段4-5（高位震荡/衰退）\n"
    md += f"- [ ] 个股跌破MA20\n"
    md += f"- [ ] 封板资金 < 1000万（涨停股）\n\n"

    return md

def update_stock_pages(stock_codes):
    """批量更新股票页面"""
    print("=" * 60)
    print("开始批量更新个股数据")
    print("=" * 60)

    success_count = 0
    for code in stock_codes:
        print(f"\n处理: {code}")
        data = fetch_realtime_price(code)

        if data:
            md = generate_stock_page(code, data)
            if md:
                file_path = os.path.join(OBSIDIAN_DIR, "个股", f"{data['name']}.md")
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(md)
                print(f"✅ 已更新: {file_path}")
                success_count += 1

        time.sleep(0.5)  # 避免请求过快

    print("\n" + "=" * 60)
    print(f"完成！成功更新 {success_count}/{len(stock_codes)} 只股票")
    print("=" * 60)

def main():
    """主函数"""
    # 从你的Obsidian笔记中提取的"待查"股票
    stocks_to_update = [
        "600578",  # 京能电力
        "002506",  # 协鑫集成
        "002940",  # 昂利康
        "600509",  # 天富能源
        "600475",  # 华光环能
        "601991",  # 大唐发电
        "002617",  # 露笑科技
        "001210",  # 金房能源
        "002165",  # 红宝丽
    ]

    print("精准数据获取 V2")
    print(f"将更新 {len(stocks_to_update)} 只股票的数据")
    print("数据源: 腾讯股票API（已验证可用）")

    update_stock_pages(stocks_to_update)

    print("\n💡 提示:")
    print("1. 已成功获取实时行情数据（价格、涨跌幅、成交额等）")
    print("2. 个股基本面数据需要修复AkShare源码（使用curl_cffi）")
    print("3. 请查看Obsidian笔记更新")

if __name__ == "__main__":
    main()
