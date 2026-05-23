#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
代理管理器 - 全局支持HTTP/SOCKS5代理
支持akshare、mootdx、requests等所有数据源
带详细注释，直接复制就能跑
"""

import os
import sys
import time
import json
import socket
from typing import Optional, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ==================== 配置区域 ====================
# 直接修改这里的代理配置，无需其他设置

# 代理配置（根据需求选择一种，不需要的设为None）
PROXY_CONFIG = {
    # HTTP/HTTPS代理（示例）
    'http': 'http://127.0.0.1:7890',   # 改成你的代理地址
    'https': 'http://127.0.0.1:7890',  # 改成你的代理地址

    # 或者使用SOCKS5代理（取消注释使用）
    # 'http': 'socks5://127.0.0.1:7891',
    # 'https': 'socks5://127.0.0.1:7891',

    # 如果不使用代理，设为None
    # 'http': None,
    # 'https': None,
}

# 请求配置
REQUEST_CONFIG = {
    'timeout': 15,           # 请求超时时间（秒）
    'retry_total': 3,        # 重试次数
    'retry_backoff': 0.5,    # 重试延迟（秒）
    'delay_between': 1.5,    # 每次请求间隔（秒），防封禁
}

# 缓存配置
CACHE_CONFIG = {
    'enabled': True,         # 是否开启缓存
    'cache_dir': './cache',  # 缓存目录
    'cache_ttl': 300,        # 缓存有效期（秒），300秒=5分钟
}
# ==================================================


class ProxyManager:
    """代理管理器 - 全局管理所有网络请求"""

    def __init__(self, proxy_config: Optional[Dict] = None,
                 request_config: Optional[Dict] = None,
                 cache_config: Optional[Dict] = None):
        """
        初始化代理管理器

        Args:
            proxy_config: 代理配置字典，格式: {'http': '...', 'https': '...'}
            request_config: 请求配置（超时、重试、延迟）
            cache_config: 缓存配置
        """
        # 使用传入的配置，或默认配置
        self.proxy_config = proxy_config or PROXY_CONFIG
        self.request_config = request_config or REQUEST_CONFIG
        self.cache_config = cache_config or CACHE_CONFIG

        # 创建session（复用连接，提升性能）
        self.session = self._create_session()

        # 初始化缓存目录
        if self.cache_config.get('enabled'):
            os.makedirs(self.cache_config.get('cache_dir'), exist_ok=True)

        # 打印配置信息
        self._print_config()

    def _create_session(self) -> requests.Session:
        """
        创建带重试机制的requests Session
        自动处理代理、超时、重试
        """
        session = requests.Session()

        # 设置代理
        if self.proxy_config.get('http') or self.proxy_config.get('https'):
            session.proxies.update({
                'http': self.proxy_config.get('http'),
                'https': self.proxy_config.get('https'),
            })
            print(f"✅ 代理已设置: HTTP={self.proxy_config.get('http')}, HTTPS={self.proxy_config.get('https')}")

        # 设置重试策略
        retry_strategy = Retry(
            total=self.request_config.get('retry_total', 3),  # 总重试次数
            backoff_factor=self.request_config.get('retry_backoff', 0.5),  # 重试延迟
            status_forcelist=[429, 500, 502, 503, 504],  # 这些状态码自动重试
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],  # 允许重试的方法
        )

        # 将重试策略挂载到session
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _print_config(self):
        """打印当前配置信息"""
        print("=" * 60)
        print("代理管理器配置信息")
        print("=" * 60)
        print(f"代理HTTP: {self.proxy_config.get('http') or '未设置'}")
        print(f"代理HTTPS: {self.proxy_config.get('https') or '未设置'}")
        print(f"请求超时: {self.request_config.get('timeout')}秒")
        print(f"重试次数: {self.request_config.get('retry_total')}次")
        print(f"请求间隔: {self.request_config.get('delay_between')}秒")
        print(f"缓存开启: {self.cache_config.get('enabled')}")
        if self.cache_config.get('enabled'):
            print(f"缓存目录: {self.cache_config.get('cache_dir')}")
            print(f"缓存有效期: {self.cache_config.get('cache_ttl')}秒")
        print("=" * 60)

    def get(self, url: str, params: Optional[Dict] = None,
            use_cache: bool = True) -> requests.Response:
        """
        发送GET请求（自动处理代理、重试、缓存、延迟）

        Args:
            url: 请求URL
            params: URL参数
            use_cache: 是否使用缓存

        Returns:
            requests.Response对象
        """
        # 生成缓存key
        cache_key = self._get_cache_key(url, params)
        cache_file = os.path.join(self.cache_config.get('cache_dir'), f"{cache_key}.json")

        # 尝试从缓存读取
        if use_cache and self.cache_config.get('enabled'):
            cached_data = self._read_cache(cache_file)
            if cached_data:
                print(f"📦 使用缓存: {url[:50]}...")
                return cached_data

        # 请求延迟（防封禁）
        if hasattr(self, '_last_request_time'):
            elapsed = time.time() - self._last_request_time
            if elapsed < self.request_config.get('delay_between', 1.5):
                sleep_time = self.request_config.get('delay_between', 1.5) - elapsed
                print(f"⏳ 请求延迟: {sleep_time:.2f}秒（防封禁）")
                time.sleep(sleep_time)

        # 发送请求
        try:
            print(f"🌐 发送请求: {url[:80]}...")
            response = self.session.get(
                url,
                params=params,
                timeout=self.request_config.get('timeout', 15)
            )
            response.raise_for_status()

            # 记录请求时间（用于延迟计算）
            self._last_request_time = time.time()

            # 写入缓存
            if use_cache and self.cache_config.get('enabled'):
                self._write_cache(cache_file, response)

            print(f"✅ 请求成功: {response.status_code}")
            return response

        except Exception as e:
            print(f"❌ 请求失败: {e}")
            raise

    def _get_cache_key(self, url: str, params: Optional[Dict]) -> str:
        """生成缓存文件名（基于URL和参数）"""
        import hashlib
        raw = url + json.dumps(params or {}, sort_keys=True)
        return hashlib.md5(raw.encode()).hexdigest()

    def _read_cache(self, cache_file: str) -> Optional[requests.Response]:
        """读取缓存（如果未过期）"""
        if not os.path.exists(cache_file):
            return None

        # 检查缓存是否过期
        mtime = os.path.getmtime(cache_file)
        if time.time() - mtime > self.cache_config.get('cache_ttl', 300):
            print(f"⏰ 缓存已过期: {cache_file}")
            return None

        # 读取缓存
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached = json.load(f)
                # 构造伪Response对象
                response = requests.Response()
                response._content = json.dumps(cached.get('content')).encode()
                response.status_code = cached.get('status_code', 200)
                response.headers = cached.get('headers', {})
                return response
        except Exception as e:
            print(f"⚠️ 读取缓存失败: {e}")
            return None

    def _write_cache(self, cache_file: str, response: requests.Response):
        """写入缓存"""
        try:
            cached = {
                'url': response.url,
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'content': response.json() if 'application/json' in response.headers.get('Content-Type', '') else response.text,
                'timestamp': time.time()
            }
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cached, f, ensure_ascii=False, indent=2)
            print(f"💾 已缓存: {cache_file}")
        except Exception as e:
            print(f"⚠️ 写入缓存失败: {e}")


# ==================== 全局单例 ====================
# 直接导入这个实例使用，无需重复创建
proxy_manager = ProxyManager()


# ==================== 便捷函数 ====================
def get_with_proxy(url: str, params: Optional[Dict] = None, **kwargs) -> requests.Response:
    """
    便捷函数：通过代理发送GET请求
    用法：和requests.get()一样，但自动走代理
    """
    return proxy_manager.get(url, params, **kwargs)


def test_proxy_connection():
    """测试代理连接是否正常"""
    print("\n" + "=" * 60)
    print("测试代理连接")
    print("=" * 60)

    test_urls = [
        'http://httpbin.org/ip',  # 测试IP
        'http://push2.eastmoney.com/api/qt/stock/get?secid=0.300442&fields=f43,f58',
        'https://www.baidu.com'
    ]

    for url in test_urls:
        try:
            response = proxy_manager.get(url, use_cache=False)
            print(f"✅ 成功: {url[:50]}... -> {response.status_code}")
            if 'ip' in url:
                print(f"   返回内容: {response.text[:100]}")
        except Exception as e:
            print(f"❌ 失败: {url[:50]}... -> {e}")

    print("=" * 60)


if __name__ == '__main__':
    # 测试代码
    print("测试代理管理器...")
    test_proxy_connection()
    print("\n使用说明：")
    print("1. 修改上方的 PROXY_CONFIG 设置你的代理")
    print("2. 直接导入 proxy_manager 使用：from proxy_manager import proxy_manager")
    print("3. 调用 get() 方法：response = proxy_manager.get('http://example.com')")
    print("4. 或者直接用便捷函数：from proxy_manager import get_with_proxy")
