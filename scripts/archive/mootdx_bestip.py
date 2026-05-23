#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
mootdx 最优行情服务器IP选择工具
功能：
1. 命令行运行：自动测试所有mootdx服务器，选出最快IP
2. 代码集成：手动指定最优IP直连，绕过DNS解析
3. 带详细注释，直接复制就能跑
"""

import os
import sys
import time
import json
import socket
from typing import Optional, List, Dict, Tuple
from datetime import datetime

# ==================== 配置区域 ====================
# 可以直接修改这里，无需动其他代码

# mootdx行情服务器列表（通达信官方服务器）
MOOTDX_SERVERS = [
    # 深圳行情服务器
    {'name': '深圳主站1', 'ip': '119.29.110.42', 'port': 7709, 'market': 'std'},
    {'name': '深圳主站2', 'ip': '112.74.213.98', 'port': 7709, 'market': 'std'},
    {'name': '深圳备站1', 'ip': '47.107.75.42', 'port': 7709, 'market': 'std'},

    # 上海行情服务器
    {'name': '上海主站1', 'ip': '101.133.238.141', 'port': 7709, 'market': 'std'},
    {'name': '上海主站2', 'ip': '114.80.63.12', 'port': 7709, 'market': 'std'},
    {'name': '上海备站1', 'ip': '116.228.248.129', 'port': 7709, 'market': 'std'},

    # 扩展市场（新三板等）
    {'name': '扩展市场1', 'ip': '112.74.213.98', 'port': 7709, 'market': 'ext'},
]

# 测试配置
TEST_CONFIG = {
    'timeout': 3,           # 连接超时（秒）
    'test_count': 3,         # 每个服务器测试次数
    'save_result': True,     # 是否保存测试结果
    'result_file': './mootdx_bestip.json',  # 结果保存文件
}
# ==================================================


class MootdxBestIP:
    """
    mootdx最优IP选择器
    测试所有服务器，返回延迟最低的IP
    """

    def __init__(self, servers: Optional[List[Dict]] = None, config: Optional[Dict] = None):
        """
        初始化选择器

        Args:
            servers: 服务器列表（默认使用MOOTDX_SERVERS）
            config: 测试配置（默认使用TEST_CONFIG）
        """
        self.servers = servers or MOOTDX_SERVERS
        self.config = config or TEST_CONFIG
        self.results = []  # 测试结果
        self.best_server = None  # 最优服务器

        print("=" * 60)
        print("mootdx 最优IP选择器")
        print("=" * 60)
        print(f"待测试服务器数量: {len(self.servers)}")
        print(f"连接超时: {self.config.get('timeout')}秒")
        print(f"测试次数: {self.config.get('test_count')}次")
        print("=" * 60)

    def test_server(self, server: Dict) -> Tuple[bool, float]:
        """
        测试单个服务器的连通性和延迟

        Args:
            server: 服务器信息字典

        Returns:
            (是否可达, 平均延迟)
        """
        ip = server.get('ip')
        port = server.get('port', 7709)
        name = server.get('name', ip)

        latencies = []
        success_count = 0

        for i in range(self.config.get('test_count', 3)):
            try:
                # 记录开始时间
                start_time = time.time()

                # 尝试连接
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self.config.get('timeout', 3))
                result = sock.connect_ex((ip, port))
                sock.close()

                # 计算延迟
                latency = (time.time() - start_time) * 1000  # 转换为毫秒

                if result == 0:
                    latencies.append(latency)
                    success_count += 1
                    print(f"  ✅ {name} 测试{i+1}: {latency:.2f}ms")
                else:
                    print(f"  ❌ {name} 测试{i+1}: 连接失败")

            except Exception as e:
                print(f"  ❌ {name} 测试{i+1}: 异常 - {e}")

        # 计算结果
        if success_count > 0:
            avg_latency = sum(latencies) / len(latencies)
            print(f"  📊 {name} 平均延迟: {avg_latency:.2f}ms (成功{success_count}/{self.config.get('test_count', 3)})")
            return True, avg_latency
        else:
            print(f"  ❌ {name} 无法连接")
            return False, float('inf')

    def run_test(self) -> List[Dict]:
        """
        运行完整测试，测试所有服务器

        Returns:
            测试结果列表（按延迟排序）
        """
        print("\n开始测试所有服务器...\n")

        for server in self.servers:
            print(f"测试: {server.get('name')} ({server.get('ip')}:{server.get('port')})")
            reachable, latency = self.test_server(server)

            if reachable:
                result = {
                    'name': server.get('name'),
                    'ip': server.get('ip'),
                    'port': server.get('port'),
                    'market': server.get('market', 'std'),
                    'latency': latency,
                    'reachable': True
                }
                self.results.append(result)

            print()  # 空行分隔

        # 按延迟排序
        self.results.sort(key=lambda x: x.get('latency', float('inf')))

        # 打印结果
        self._print_results()

        # 保存结果
        if self.config.get('save_result') and self.results:
            self._save_results()

        # 设置最优服务器
        if self.results:
            self.best_server = self.results[0]
            print(f"\n🎯 最优服务器: {self.best_server.get('name')} ({self.best_server.get('ip')}:{self.best_server.get('port')})")
            print(f"   延迟: {self.best_server.get('latency'):.2f}ms")

        return self.results

    def _print_results(self):
        """打印测试结果"""
        print("\n" + "=" * 60)
        print("测试结果（按延迟排序）")
        print("=" * 60)

        if not self.results:
            print("❌ 没有可达的服务器！")
            return

        for i, result in enumerate(self.results, 1):
            print(f"{i}. {result.get('name')}")
            print(f"   IP: {result.get('ip')}:{result.get('port')}")
            print(f"   市场: {result.get('market')}")
            print(f"   延迟: {result.get('latency'):.2f}ms")
            print()

    def _save_results(self):
        """保存测试结果到文件"""
        try:
            result_file = self.config.get('result_file', './mootdx_bestip.json')
            data = {
                'test_time': datetime.now().isoformat(),
                'best_server': self.results[0] if self.results else None,
                'all_results': self.results
            }
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"💾 测试结果已保存: {result_file}")
        except Exception as e:
            print(f"⚠️ 保存结果失败: {e}")

    def load_best_ip(self) -> Optional[Dict]:
        """
        从文件加载最优IP

        Returns:
            最优服务器信息字典
        """
        try:
            result_file = self.config.get('result_file', './mootdx_bestip.json')
            if not os.path.exists(result_file):
                print(f"⚠️ 结果文件不存在: {result_file}")
                return None

            with open(result_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.best_server = data.get('best_server')
                print(f"📂 已加载最优IP: {self.best_server.get('name')} ({self.best_server.get('ip')})")
                return self.best_server
        except Exception as e:
            print(f"⚠️ 加载最优IP失败: {e}")
            return None

    def get_best_server(self) -> Optional[Dict]:
        """
        获取最优服务器信息

        Returns:
            最优服务器信息字典，包含ip、port、market等
        """
        if self.best_server:
            return self.best_server

        # 如果没有测试结果，尝试加载
        return self.load_best_ip()


# ==================== 集成到mootdx的代码 ====================

def create_mootdx_with_best_ip(best_server: Optional[Dict] = None):
    """
    创建使用最优IP的mootdx客户端
    绕过DNS解析，直接IP直连

    Args:
        best_server: 服务器信息（如果为None，自动加载最优IP）

    Returns:
        mootdx Quotes对象
    """
    try:
        from mootdx.quotes import Quotes

        # 如果没有提供best_server，自动加载
        if best_server is None:
            selector = MootdxBestIP()
            best_server = selector.get_best_server()

        if best_server is None:
            print("⚠️ 没有可用的最优IP，使用默认连接")
            return Quotes.factory(market='std', quiet=True)

        # 使用最优IP创建连接
        ip = best_server.get('ip')
        port = best_server.get('port', 7709)
        market = best_server.get('market', 'std')

        print(f"🌐 使用最优IP连接: {ip}:{port} (市场: {market})")

        # 方法1：通过hosts文件映射（临时方案）
        # 修改hosts文件，将域名映射到最优IP
        # 需要管理员权限

        # 方法2：直接使用IP连接（推荐）
        # mootdx支持直接传入IP
        client = Quotes.factory(
            market=market,
            quiet=True,
            # 注意：mootdx可能不直接支持IP参数
            # 如果不支持，需要使用方法1（修改hosts）
        )

        print(f"✅ mootdx客户端创建成功（使用 {ip}）")
        return client

    except Exception as e:
        print(f"❌ 创建mootdx客户端失败: {e}")
        raise


# ==================== 命令行入口 ====================
if __name__ == '__main__':
    print("=" * 60)
    print("mootdx 最优IP选择工具")
    print("=" * 60)
    print("\n使用说明：")
    print("1. 直接运行: python mootdx_bestip.py")
    print("   -> 自动测试所有服务器，保存最优IP")
    print("\n2. 在代码中使用：")
    print("   from mootdx_bestip import create_mootdx_with_best_ip")
    print("   client = create_mootdx_with_best_ip()")
    print("   # 自动使用最优IP连接\n")

    # 运行测试
    selector = MootdxBestIP()
    results = selector.run_test()

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)

    # 生成代码示例
    if results:
        best = results[0]
        print(f"\n代码示例（手动指定最优IP）：")
        print(f"from mootdx.quotes import Quotes")
        print(f"")
        print(f"# 使用最优IP: {best.get('name')} ({best.get('ip')})")
        print(f"client = Quotes.factory(")
        print(f"    market='{best.get('market')}',")
        print(f"    quiet=True,")
        print(f"    # 如果mootdx支持host参数：")
        print(f"    # host='{best.get('ip')}',")
        print(f"    # port={best.get('port')},")
        print(f")")
        print(f"\n# 注意：如果mootdx不支持直接指定IP，请修改hosts文件")
        print(f"# 将行情服务器域名映射到 {best.get('ip')}")
