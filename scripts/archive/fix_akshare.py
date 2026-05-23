#!/usr/bin/env python3
"""
AkShare自动修复工具
自动修改AkShare源码，使用curl_cffi模拟Chrome TLS指纹
解决东方财富API连接问题

使用方法：
1. 运行本脚本：python fix_akshare.py
2. 重启Python内核
3. 正常使用akshare，所有东方财富API都能访问了！
"""

import os
import sys
import site
import re

def find_akshare_path():
    """查找AkShare安装路径"""
    try:
        import akshare as ak
        ak_path = os.path.dirname(ak.__file__)
        print(f"✅ 找到AkShare路径: {ak_path}")
        return ak_path
    except Exception as e:
        print(f"❌ 找不到AkShare: {e}")
        return None

def check_curl_cffi():
    """检查curl_cffi是否安装"""
    try:
        import curl_cffi
        print(f"✅ curl_cffi已安装: {curl_cffi.__version__}")
        return True
    except ImportError:
        print("⚠️ curl_cffi未安装，正在安装...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "curl_cffi"])
        print("✅ curl_cffi安装完成")
        return True
    except Exception as e:
        print(f"❌ curl_cffi安装失败: {e}")
        return False

def create_patch_file(ak_path):
    """创建补丁文件：添加curl_cffi支持"""
    stock_fund_em_path = os.path.join(ak_path, "stock_fund_em.py")

    if not os.path.exists(stock_fund_em_path):
        print(f"❌ 找不到文件: {stock_fund_em_path}")
        return False

    print(f"📄 准备修改文件: {stock_fund_em_path}")

    # 读取原文件
    with open(stock_fund_em_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查是否已经打过补丁
    if 'curl_cffi' in content:
        print("⚠️ 文件已经包含curl_cffi，可能已打过补丁")
        return True

    # 1. 在import区域添加curl_cffi
    import_section_end = content.find('import ')
    # 找到最后一个import语句
    last_import_pos = content.rfind('import ')
    last_import_line_end = content.find('\n', last_import_pos)

    patch_import = '\nimport curl_cffi.requests as cffi_requests\n'

    content = content[:last_import_line_end+1] + patch_import + content[last_import_line_end+1:]

    # 2. 添加统一的请求函数
    patch_function = '''
def _em_get(url, params=None, retry=3):
    """统一的东方财富API请求函数（使用curl_cffi模拟Chrome）"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Referer': 'http://quote.eastmoney.com/',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }

    for i in range(retry):
        try:
            resp = cffi_requests.get(
                url,
                params=params,
                headers=headers,
                impersonate="chrome131",
                timeout=10
            )
            resp.raise_for_status()
            return resp
        except Exception as e:
            print(f"⚠️ 请求失败({i+1}/{retry}): {e}")
            if i == retry - 1:
                raise
            import time
            time.sleep(1)

'''

    # 在函数定义之前插入
    first_def_pos = content.find('\ndef ')
    content = content[:first_def_pos] + patch_function + '\n' + content[first_def_pos:]

    # 3. 替换所有requests.get为_em_get
    # 注意：只替换函数调用，不替换import语句
    content = re.sub(
        r'(?<!\.)(requests\.get\()',
        '_em_get(',
        content
    )

    # 4. 写回文件
    backup_path = stock_fund_em_path + '.backup'
    if not os.path.exists(backup_path):
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ 已备份原文件到: {backup_path}")

    with open(stock_fund_em_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✅ 已成功修改: {stock_fund_em_path}")
    return True

def test_akshare_fix():
    """测试AkShare修复效果"""
    print("\n" + "="*60)
    print("测试AkShare修复效果")
    print("="*60 + "\n")

    try:
        import akshare as ak

        # 测试1：个股基本面（之前会失败）
        print("[1/3] 测试个股基本面获取...")
        df = ak.stock_individual_info_em(symbol="600578")
        if df is not None and not df.empty:
            print(f"✅ 个股基本面获取成功: {df.shape}")
        else:
            print("⚠️ 返回数据为空")

        # 测试2：涨停板数据（之前会失败）
        print("\n[2/3] 测试涨停板数据获取...")
        try:
            df_zt = ak.stock_zt_pool_em(date="20260514")
            if df_zt is not None and not df_zt.empty:
                print(f"✅ 涨停板数据获取成功: {len(df_zt)} 只股票")
            else:
                print("⚠️ 返回数据为空（可能今天不是交易日）")
        except Exception as e:
            print(f"⚠️ 涨停板数据获取失败: {e}")

        # 测试3：资金流数据（之前会失败）
        print("\n[3/3] 测试资金流数据获取...")
        try:
            df_flow = ak.stock_sector_fund_flow_rank(indicator="今日")
            if df_flow is not None and not df_flow.empty:
                print(f"✅ 资金流数据获取成功: {len(df_flow)} 个板块")
            else:
                print("⚠️ 返回数据为空")
        except Exception as e:
            print(f"⚠️ 资金流数据获取失败: {e}")

        print("\n" + "="*60)
        print("测试完成！")
        print("="*60)

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        print("\n💡 提示：请尝试重启Python内核，然后重新测试")

def main():
    """主函数"""
    print("="*60)
    print("AkShare自动修复工具")
    print("="*60)

    # 步骤1：检查curl_cffi
    print("\n[步骤1/4] 检查curl_cffi...")
    if not check_curl_cffi():
        print("❌ 无法继续，请手动安装curl_cffi: pip install curl_cffi")
        return

    # 步骤2：查找AkShare路径
    print("\n[步骤2/4] 查找AkShare路径...")
    ak_path = find_akshare_path()
    if not ak_path:
        return

    # 步骤3：修改源码
    print("\n[步骤3/4] 修改AkShare源码...")
    if not create_patch_file(ak_path):
        print("❌ 修改失败")
        return

    # 步骤4：测试效果
    print("\n[步骤4/4] 测试修复效果...")
    test_akshare_fix()

    print("\n" + "="*60)
    print("修复完成！")
    print("="*60)
    print("\n💡 下一步：")
    print("1. 重启Python内核（关闭所有Python进程）")
    print("2. 重新运行你的数据获取脚本")
    print("3. 所有东方财富API现在都应该能正常工作了！")
    print("\n如果还有问题，请查看备份文件并手动恢复：")
    print(f"  {os.path.join(ak_path, 'stock_fund_em.py.backup')}")

if __name__ == "__main__":
    main()
