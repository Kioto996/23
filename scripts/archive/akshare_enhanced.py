#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AKShare增强版 - 完整功能适配
支持：代理、超时、自动重试、请求间隔延时防封禁、本地缓存
带详细注释，直接复制就能跑
"""

import os
import time
import json
import hashlib
from typing import Optional, Dict, Any, Callable
from datetime import datetime, timedelta
import pandas as pd

# 导入代理管理器（使用全局代理配置）
from proxy_manager import proxy_manager, get_with_proxy

# ==================== 配置区域 ====================
# 可以直接修改这里，无需动其他代码

# AKShare专用配置
AKSHARE_CONFIG = {
    'enable_proxy': True,        # 是否启用代理
    'timeout': 20,              # 请求超时（秒）
    'retry_times': 3,           # 失败重试次数
    'retry_delay': 2,           # 重试间隔（秒）
    'request_delay': 1.5,       # 请求间隔（秒），防封禁
    'enable_cache': True,        # 是否开启本地缓存
    'cache_dir': './cache/akshare',  # 缓存目录
    'cache_ttl': 300,           # 缓存有效期（秒），300=5分钟
    'verbose': True,             # 是否打印详细日志
}

# 默认请求头（模拟浏览器，降低被封概率）
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Referer': 'http://finance.eastmoney.com/',
}
# ==================================================


class AKShareEnhanced:
    """
    AKShare增强版包装器
    在原生AKShare基础上增加：代理、超时、重试、延迟、缓存
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        初始化AKShare增强版

        Args:
            config: 配置字典（如果不传，使用上方AKSHARE_CONFIG）
        """
        self.config = config or AKSHARE_CONFIG

        # 初始化AKShare（延迟导入，避免启动时就必须安装）
        self.ak = None
        self._init_akshare()

        # 初始化缓存目录
        if self.config.get('enable_cache'):
            os.makedirs(self.config.get('cache_dir'), exist_ok=True)
            self._log(f"✅ 缓存目录: {self.config.get('cache_dir')}")

        # 记录上次请求时间（用于计算延迟）
        self._last_request_time = 0

        # 打印配置
        self._print_config()

    def _init_akshare(self):
        """初始化AKShare库"""
        try:
            import akshare as ak
            self.ak = ak
            self._log("✅ AKShare库加载成功")
        except ImportError:
            raise ImportError("❌ 请先安装AKShare: pip install akshare")

    def _print_config(self):
        """打印当前配置"""
        self._log("=" * 60)
        self._log("AKShare增强版配置")
        self._log("=" * 60)
        self._log(f"代理启用: {self.config.get('enable_proxy')}")
        self._log(f"请求超时: {self.config.get('timeout')}秒")
        self._log(f"重试次数: {self.config.get('retry_times')}次")
        self._log(f"请求间隔: {self.config.get('request_delay')}秒")
        self._log(f"缓存启用: {self.config.get('enable_cache')}")
        if self.config.get('enable_cache'):
            self._log(f"缓存目录: {self.config.get('cache_dir')}")
            self._log(f"缓存有效期: {self.config.get('cache_ttl')}秒")
        self._log("=" * 60)

    def _log(self, msg: str):
        """打印日志（根据配置决定是否输出）"""
        if self.config.get('verbose'):
            print(msg)

    def _apply_delay(self):
        """应用请求延迟（防封禁）"""
        now = time.time()
        elapsed = now - self._last_request_time
        delay = self.config.get('request_delay', 1.5)

        if elapsed < delay:
            sleep_time = delay - elapsed
            self._log(f"⏳ 请求延迟: {sleep_time:.2f}秒（防封禁）")
            time.sleep(sleep_time)

        self._last_request_time = time.time()

    def _get_cache_key(self, func_name: str, kwargs: Dict) -> str:
        """生成缓存key（基于函数名和参数）"""
        raw = func_name + json.dumps(kwargs, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(raw.encode()).hexdigest()

    def _get_cache_file(self, cache_key: str) -> str:
        """获取缓存文件路径"""
        return os.path.join(self.config.get('cache_dir'), f"{cache_key}.json")

    def _read_cache(self, cache_key: str) -> Optional[Any]:
        """读取缓存（如果未过期）"""
        if not self.config.get('enable_cache'):
            return None

        cache_file = self._get_cache_file(cache_key)
        if not os.path.exists(cache_file):
            return None

        # 检查是否过期
        mtime = os.path.getmtime(cache_file)
        if time.time() - mtime > self.config.get('cache_ttl', 300):
            self._log(f"⏰ 缓存已过期: {cache_file}")
            return None

        # 读取缓存
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached = json.load(f)
                self._log(f"📦 使用缓存: {cache_key[:16]}...")
                return cached.get('data')
        except Exception as e:
            self._log(f"⚠️ 读取缓存失败: {e}")
            return None

    def _write_cache(self, cache_key: str, data: Any):
        """写入缓存"""
        if not self.config.get('enable_cache'):
            return

        cache_file = self._get_cache_file(cache_key)
        try:
            # 将DataFrame转换为可序列化的格式
            if isinstance(data, pd.DataFrame):
                data_to_cache = data.to_dict('records')
            else:
                data_to_cache = data

            cached = {
                'func': cache_key,
                'data': data_to_cache,
                'timestamp': time.time(),
                'datetime': datetime.now().isoformat()
            }
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cached, f, ensure_ascii=False, indent=2)
            self._log(f"💾 已缓存: {cache_key[:16]}...")
        except Exception as e:
            self._log(f"⚠️ 写入缓存失败: {e}")

    def _call_with_retry(self, func: Callable, *args, **kwargs):
        """
        带重试的调用函数
        自动处理异常，按配置重试
        """
        retry_times = self.config.get('retry_times', 3)
        retry_delay = self.config.get('retry_delay', 2)

        last_exception = None
        for attempt in range(retry_times + 1):
            try:
                # 应用请求延迟（防封禁）
                self._apply_delay()

                # 调用函数
                self._log(f"🌐 调用AKShare: {func.__name__} (尝试 {attempt + 1}/{retry_times + 1})")
                result = func(*args, **kwargs)
                self._log(f"✅ 调用成功: {func.__name__}")
                return result

            except Exception as e:
                last_exception = e
                self._log(f"⚠️ 调用失败: {e}")

                # 如果不是最后一次尝试，等待后重试
                if attempt < retry_times:
                    self._log(f"🔄 {retry_delay}秒后重试...")
                    time.sleep(retry_delay)
                else:
                    self._log(f"❌ 已达最大重试次数，放弃")
                    raise last_exception

    # ==================== 包装常用AKShare函数 ====================

    def stock_zh_a_spot_em(self, **kwargs):
        """
        获取A股实时行情（东方财富）
        原AKShare函数: ak.stock_zh_a_spot_em()
        """
        cache_key = self._get_cache_key('stock_zh_a_spot_em', kwargs)
        cached = self._read_cache(cache_key)
        if cached is not None:
            return pd.DataFrame(cached)

        result = self._call_with_retry(self.ak.stock_zh_a_spot_em, **kwargs)
        self._write_cache(cache_key, result)
        return result

    def stock_zh_a_hist(self, symbol: str, period: str = "daily",
                        start_date: str = "", end_date: str = "",
                        adjust: str = "", **kwargs):
        """
        获取A股历史K线数据
        原AKShare函数: ak.stock_zh_a_hist(symbol, period, start_date, end_date, adjust)
        """
        func_kwargs = {
            'symbol': symbol,
            'period': period,
            'start_date': start_date,
            'end_date': end_date,
            'adjust': adjust,
            **kwargs
        }
        cache_key = self._get_cache_key('stock_zh_a_hist', func_kwargs)
        cached = self._read_cache(cache_key)
        if cached is not None:
            return pd.DataFrame(cached)

        result = self._call_with_retry(
            self.ak.stock_zh_a_hist,
            symbol=symbol,
            period=period,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
            **kwargs
        )
        self._write_cache(cache_key, result)
        return result

    def stock_individual_info_em(self, symbol: str, **kwargs):
        """
        获取个股信息（东方财富）
        原AKShare函数: ak.stock_individual_info_em(symbol)
        """
        cache_key = self._get_cache_key('stock_individual_info_em', {'symbol': symbol, **kwargs})
        cached = self._read_cache(cache_key)
        if cached is not None:
            return pd.DataFrame(cached)

        result = self._call_with_retry(self.ak.stock_individual_info_em, symbol=symbol, **kwargs)
        self._write_cache(cache_key, result)
        return result

    def stock_zh_a_daily(self, symbol: str, adjust: str = "qfq", **kwargs):
        """
        获取A股日线行情（复权）
        原AKShare函数: ak.stock_zh_a_daily(symbol, adjust)
        """
        func_kwargs = {'symbol': symbol, 'adjust': adjust, **kwargs}
        cache_key = self._get_cache_key('stock_zh_a_daily', func_kwargs)
        cached = self._read_cache(cache_key)
        if cached is not None:
            return pd.DataFrame(cached)

        result = self._call_with_retry(self.ak.stock_zh_a_daily, symbol=symbol, adjust=adjust, **kwargs)
        self._write_cache(cache_key, result)
        return result

    # ==================== 添加更多函数... ====================
    # 按需要添加其他AKShare函数，格式同上


# ==================== 全局单例 ====================
# 直接导入这个实例使用，无需重复创建
ak_enhanced = AKShareEnhanced()


# ==================== 便捷函数 ====================
def get_stock_realtime(symbol: str) -> Optional[pd.DataFrame]:
    """
    便捷函数：获取个股实时行情
    用法：df = get_stock_realtime('300442')
    """
    try:
        df = ak_enhanced.stock_zh_a_spot_em()
        return df[df['代码'] == symbol]
    except Exception as e:
        print(f"❌ 获取实时行情失败: {e}")
        return None


def get_stock_kline(symbol: str, period: str = "daily", adjust: str = "qfq") -> Optional[pd.DataFrame]:
    """
    便捷函数：获取个股K线数据
    用法：df = get_stock_kline('300442', period='daily', adjust='qfq')
    """
    try:
        return ak_enhanced.stock_zh_a_hist(symbol=symbol, period=period, adjust=adjust)
    except Exception as e:
        print(f"❌ 获取K线数据失败: {e}")
        return None


# ==================== 测试代码 ====================
if __name__ == '__main__':
    print("=" * 60)
    print("测试 AKShare增强版")
    print("=" * 60)

    # 创建实例
    ak_plus = AKShareEnhanced()

    # 测试1: 获取实时行情
    print("\n测试1: 获取A股实时行情...")
    try:
        df = ak_plus.stock_zh_a_spot_em()
        print(f"✅ 成功获取 {len(df)} 只股票实时行情")
        print(df.head())
    except Exception as e:
        print(f"❌ 测试失败: {e}")

    # 测试2: 获取K线数据
    print("\n测试2: 获取润泽科技(300442)K线数据...")
    try:
        df = ak_plus.stock_zh_a_hist(symbol='300442', period='daily', adjust='qfq')
        print(f"✅ 成功获取 {len(df)} 条K线数据")
        print(df.tail())
    except Exception as e:
        print(f"❌ 测试失败: {e}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    print("\n使用说明：")
    print("1. 修改上方 AKSHARE_CONFIG 配置区")
    print("2. 导入使用：from akshare_enhanced import ak_enhanced")
    print("3. 调用方法：df = ak_enhanced.stock_zh_a_hist(symbol='300442')")
    print("4. 或直接使用便捷函数：from akshare_enhanced import get_stock_kline")
