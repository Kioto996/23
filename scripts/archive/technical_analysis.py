#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
technical_analysis.py - 技术面分析模块（完整版）
集成：代理管理器 + AKShare增强版 + mootdx最优IP

功能：
1. 全局HTTP/SOCKS5代理支持
2. AKShare：代理、超时、重试、延迟、缓存
3. mootdx：最优IP选择、手动指定IP直连
4. 所有代码带详细注释，直接复制就能跑

数据源优先级：
1. 东方财富API（已验证可用，走代理）
2. AKShare增强版（代理+缓存+重试）
3. mootdx（最优IP直连）
"""

import os
import sys
import time
import warnings
from typing import Optional, Dict, Any
import pandas as pd
import numpy as np

warnings.filterwarnings('ignore')

# ==================== 导入自定义模块 ====================
# 代理管理器（全局代理支持）
from proxy_manager import proxy_manager, get_with_proxy

# AKShare增强版（代理+超时+重试+延迟+缓存）
from akshare_enhanced import AKShareEnhanced, ak_enhanced

# mootdx最优IP选择
from mootdx_bestip import MootdxBestIP, create_mootdx_with_best_ip

# =====================================================


# ==================== 配置区域 ====================
# 可以直接修改这里，无需动其他代码

# 请求延迟配置（避免触发反爬）
REQUEST_DELAY = 1.5  # 每次请求后延迟1.5秒

# 是否使用代理（全局开关）
USE_PROXY = True

# 是否使用AKShare增强版（带缓存和重试）
USE_AKSHARE_ENHANCED = True

# 是否使用mootdx最优IP
USE_MOOTDX_BEST_IP = True

# =====================================================


class TechnicalAnalyzer:
    """
    技术面分析器 - 集成所有数据源
    支持代理、缓存、重试、最优IP
    """

    def __init__(self, market='std', use_proxy: bool = USE_PROXY):
        """
        初始化分析器

        Args:
            market: 市场类型，'std'=标准市场(沪深)，'ext'=扩展市场(新三板)
            use_proxy: 是否使用代理
        """
        self.market = market
        self.use_proxy = use_proxy
        self.mootdx_client = None
        self.use_mootdx = False
        self.use_akshare = False
        self.use_eastmoney_api = False

        # 初始化AKShare增强版
        if USE_AKSHARE_ENHANCED:
            try:
                self.ak_enhanced = AKShareEnhanced()
                self.use_akshare = True
                print("✅ AKShare增强版初始化成功")
            except Exception as e:
                print(f"⚠️ AKShare增强版初始化失败: {e}")
                self.use_akshare = False

        # 测试并选择数据源（优先级：东方财富API > AKShare > mootdx）
        if self._test_eastmoney_api():
            self.use_eastmoney_api = True
            print("✅ 使用东方财富API作为主数据源")
            return

        # 回退到AKShare增强版
        if self.use_akshare:
            print("✅ 使用AKShare增强版作为数据源")
            return

        # 回退到mootdx（使用最优IP）
        if USE_MOOTDX_BEST_IP:
            if self._connect_mootdx_best_ip():
                print("✅ 使用mootdx（最优IP）作为数据源")
                return

        # 所有数据源都失败
        raise Exception("❌ 所有真实数据源都不可用！请检查网络连接和代理配置。")

    def _test_eastmoney_api(self) -> bool:
        """
        测试东方财富API是否可用
        使用代理管理器发送请求
        """
        try:
            url = "http://push2.eastmoney.com/api/qt/stock/get"
            params = {
                "secid": "0.300442",
                "fields": "f43,f44,f45,f46,f47,f48,f57,f58,f170"
            }

            # 使用代理管理器发送请求
            response = get_with_proxy(url, params=params)

            if response.status_code == 200:
                data = response.json()
                if data.get('data') and 'f43' in data['data']:
                    print("✅ 东方财富API测试成功")
                    return True

        except Exception as e:
            print(f"⚠️ 东方财富API不可用: {e}")

        return False

    def _connect_mootdx_best_ip(self) -> bool:
        """
        连接mootdx，使用最优IP
        绕过DNS解析，直接IP直连
        """
        try:
            from mootdx.quotes import Quotes

            # 获取最优IP
            selector = MootdxBestIP()
            best_server = selector.get_best_server()

            if best_server is None:
                print("⚠️ 没有最优IP，运行测试...")
                selector.run_test()
                best_server = selector.get_best_server()

            if best_server:
                self.mootdx_client = create_mootdx_with_best_ip(best_server)
                self.use_mootdx = True
                print(f"✅ mootdx连接成功（使用最优IP: {best_server.get('ip')}）")
                return True
            else:
                # 回退到默认连接
                print("⚠️ 没有可用IP，使用默认连接...")
                self.mootdx_client = Quotes.factory(market=self.market, quiet=True)
                self.use_mootdx = True
                return True

        except Exception as e:
            print(f"⚠️ mootdx连接失败: {e}")
            self.use_mootdx = False
            return False

    def get_realtime_quotes(self, symbol: str) -> Dict:
        """
        获取实时行情

        Args:
            symbol: 股票代码，如 '300442'

        Returns:
            实时行情字典
        """
        # 优先使用东方财富API
        if self.use_eastmoney_api:
            result = self._fetch_from_eastmoney(symbol)
            if result:
                return result
            else:
                print("⚠️ 东方财富API失败，尝试其他数据源...")

        # 回退到AKShare增强版
        if self.use_akshare:
            try:
                result = self._fetch_from_akshare_enhanced(symbol)
                if result:
                    return result
            except Exception as e:
                print(f"⚠️ AKShare增强版获取失败: {e}，尝试mootdx...")

        # 回退到mootdx
        if self.use_mootdx:
            try:
                result = self._fetch_from_mootdx(symbol)
                if result:
                    return result
            except Exception as e:
                print(f"❌ mootdx获取失败: {e}")

        # 所有数据源都失败
        raise Exception(f"❌ 所有数据源都无法获取 {symbol} 的实时行情！")

    def _fetch_from_eastmoney(self, symbol: str) -> Optional[Dict]:
        """从东方财富API获取实时行情（使用代理）"""
        try:
            # 判断市场：0=深圳, 1=上海
            if symbol.startswith('6'):
                secid = f"1.{symbol}"
            else:
                secid = f"0.{symbol}"

            url = "http://push2.eastmoney.com/api/qt/stock/get"
            params = {
                "secid": secid,
                "fields": "f43,f44,f45,f46,f47,f48,f51,f52,f57,f58,f60,f170,f171"
            }

            # 使用代理管理器
            response = get_with_proxy(url, params=params)

            if response.status_code == 200:
                data = response.json()
                if data.get('data'):
                    d = data['data']
                    # 价格字段需要除以100
                    return {
                        'symbol': symbol,
                        'name': d.get('f58', ''),
                        'price': d.get('f43', 0) / 100.0,
                        'open': d.get('f44', 0) / 100.0,
                        'high': d.get('f45', 0) / 100.0,
                        'low': d.get('f46', 0) / 100.0,
                        'pre_close': d.get('f60', 0) / 100.0,
                        'change': d.get('f171', 0) / 100.0,
                        'change_pct': d.get('f170', 0) / 100.0,
                        'volume': d.get('f47', 0),
                        'amount': d.get('f48', 0),
                        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'source': 'eastmoney_api'
                    }

        except Exception as e:
            print(f"⚠️ 东方财富API获取失败: {e}")

        return None

    def _fetch_from_akshare_enhanced(self, symbol: str) -> Optional[Dict]:
        """从AKShare增强版获取实时行情（带缓存和重试）"""
        try:
            # 使用AKShare增强版（自动处理缓存、重试、延迟）
            df = self.ak_enhanced.stock_zh_a_spot_em()
            stock_data = df[df['代码'] == symbol]

            if not stock_data.empty:
                row = stock_data.iloc[0]
                return {
                    'symbol': symbol,
                    'name': row.get('名称', ''),
                    'price': float(row.get('最新价', 0)),
                    'open': float(row.get('今开', 0)),
                    'high': float(row.get('最高', 0)),
                    'low': float(row.get('最低', 0)),
                    'pre_close': float(row.get('昨收', 0)),
                    'change': float(row.get('涨跌额', 0)),
                    'change_pct': float(row.get('涨跌幅', 0)),
                    'volume': int(row.get('成交量', 0)),
                    'amount': float(row.get('成交额', 0)),
                    'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'source': 'akshare_enhanced'
                }

        except Exception as e:
            print(f"⚠️ AKShare增强版获取失败: {e}")

        return None

    def _fetch_from_mootdx(self, symbol: str) -> Optional[Dict]:
        """从mootdx获取实时行情（使用最优IP）"""
        try:
            tdx_symbol = self._convert_to_tdx_format(symbol)
            data = self.mootdx_client.quotes(symbol=[tdx_symbol])

            if data is not None and len(data) > 0:
                result = {
                    'symbol': symbol,
                    'name': data.iloc[0].get('name', ''),
                    'price': float(data.iloc[0].get('price', 0)),
                    'open': float(data.iloc[0].get('open', 0)),
                    'high': float(data.iloc[0].get('high', 0)),
                    'low': float(data.iloc[0].get('low', 0)),
                    'pre_close': float(data.iloc[0].get('preclose', 0)),
                    'change': float(data.iloc[0].get('price', 0)) - float(data.iloc[0].get('preclose', 0)),
                    'change_pct': round((float(data.iloc[0].get('price', 0)) - float(data.iloc[0].get('preclose', 0))) / float(data.iloc[0].get('preclose', 0)) * 100, 2),
                    'volume': int(data.iloc[0].get('volume', 0)),
                    'amount': float(data.iloc[0].get('amount', 0)),
                    'time': data.iloc[0].get('time', ''),
                    'source': 'mootdx_best_ip'
                }
                return result

        except Exception as e:
            print(f"⚠️ mootdx获取失败: {e}")

        return None

    def get_kline_data(self, symbol: str, frequency: str = 'daily', offset: int = 100) -> Optional[pd.DataFrame]:
        """
        获取K线数据

        Args:
            symbol: 股票代码
            frequency: K线周期 - 'daily'(日K), 'weekly'(周K), 'monthly'(月K)
            offset: 获取条数

        Returns:
            K线数据DataFrame
        """
        # 优先使用东方财富K线API
        if self.use_eastmoney_api:
            result = self._fetch_kline_from_eastmoney(symbol, frequency, offset)
            if result is not None:
                return result
            else:
                print("⚠️ 东方财富K线API失败，尝试其他数据源...")

        # 回退到AKShare增强版
        if self.use_akshare:
            try:
                result = self._fetch_kline_from_akshare_enhanced(symbol, frequency, offset)
                if result is not None:
                    return result
            except Exception as e:
                print(f"⚠️ AKShare增强版获取K线失败: {e}，尝试mootdx...")

        # 回退到mootdx
        if self.use_mootdx:
            try:
                result = self._fetch_kline_from_mootdx(symbol, frequency, offset)
                if result is not None:
                    return result
            except Exception as e:
                print(f"❌ mootdx获取K线失败: {e}")

        # 所有数据源都失败
        raise Exception(f"❌ 所有数据源都无法获取 {symbol} 的K线数据！")

    def _fetch_kline_from_eastmoney(self, symbol: str, frequency: str = 'daily', offset: int = 100) -> Optional[pd.DataFrame]:
        """从东方财富API获取K线数据（使用代理）"""
        try:
            # 判断市场
            if symbol.startswith('6'):
                secid = f"1.{symbol}"
            else:
                secid = f"0.{symbol}"

            # 频率映射
            freq_map = {
                'daily': '101',  # 日K
                'weekly': '102',  # 周K
                'monthly': '103'  # 月K
            }
            klt = freq_map.get(frequency, '101')

            url = "http://push2his.eastmoney.com/api/qt/stock/kline/get"
            params = {
                "secid": secid,
                "fields1": "f1,f2,f3,f4,f5,f6",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
                "klt": klt,
                "fqt": "1",  # 前复权
                "end": "20500101",
                "lmt": str(offset)
            }

            # 使用代理管理器
            response = get_with_proxy(url, params=params)

            if response.status_code == 200:
                data = response.json()
                if data.get('data') and data['data'].get('klines'):
                    klines = data['data']['klines']
                    # 解析K线数据
                    parsed_data = []
                    for line in klines:
                        parts = line.split(',')
                        parsed_data.append({
                            '日期': parts[0],
                            '开盘': float(parts[1]),
                            '收盘': float(parts[2]),
                            '最高': float(parts[3]),
                            '最低': float(parts[4]),
                            '成交量': int(parts[5]),
                            '成交额': float(parts[6])
                        })

                    df = pd.DataFrame(parsed_data)
                    df['日期'] = pd.to_datetime(df['日期'])
                    df = self._calculate_indicators(df)
                    df['source'] = 'eastmoney_api'
                    return df

        except Exception as e:
            print(f"⚠️ 东方财富K线API获取失败: {e}")

        return None

    def _fetch_kline_from_akshare_enhanced(self, symbol: str, frequency: str = 'daily', offset: int = 100) -> Optional[pd.DataFrame]:
        """从AKShare增强版获取K线数据（带缓存和重试）"""
        try:
            # 使用AKShare增强版
            if frequency == 'daily':
                data = self.ak_enhanced.stock_zh_a_hist(symbol=symbol, period="daily", adjust="qfq")
            elif frequency == 'weekly':
                data = self.ak_enhanced.stock_zh_a_hist(symbol=symbol, period="weekly", adjust="qfq")
            elif frequency == 'monthly':
                data = self.ak_enhanced.stock_zh_a_hist(symbol=symbol, period="monthly", adjust="qfq")
            else:
                data = self.ak_enhanced.stock_zh_a_hist(symbol=symbol, period="daily", adjust="qfq")

            if data is not None and len(data) > 0:
                data = data.tail(offset)
                data = self._calculate_indicators(data)
                data['source'] = 'akshare_enhanced'
                return data

        except Exception as e:
            print(f"⚠️ AKShare增强版获取K线失败: {e}")

        return None

    def _fetch_kline_from_mootdx(self, symbol: str, frequency: str = 'daily', offset: int = 100) -> Optional[pd.DataFrame]:
        """从mootdx获取K线数据（使用最优IP）"""
        try:
            freq_map = {
                'daily': 4, 'weekly': 5, 'monthly': 6
            }
            freq_code = freq_map.get(frequency, 4)

            data = self.mootdx_client.bars(symbol=symbol, frequency=freq_code)

            if data is not None and len(data) > 0:
                data = data.tail(offset)
                data = self._calculate_indicators(data)
                data['source'] = 'mootdx_best_ip'
                return data

        except Exception as e:
            print(f"⚠️ mootdx获取K线失败: {e}")

        return None

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标（MACD、KDJ、RSI、布林带）"""
        try:
            # 确保列名统一
            column_map = {
                '收盘': 'close', '开盘': 'open', '最高': 'high', '最低': 'low',
                '成交量': 'volume', '成交额': 'amount'
            }
            df = df.rename(columns=column_map)

            # 确保必要的列存在
            required_cols = ['close', 'open', 'high', 'low']
            for col in required_cols:
                if col not in df.columns:
                    print(f"⚠️ 缺少必要的列: {col}")
                    return df

            # MACD
            ema12 = df['close'].ewm(span=12, adjust=False).mean()
            ema26 = df['close'].ewm(span=26, adjust=False).mean()
            df['macd_dif'] = ema12 - ema26
            df['macd_dea'] = df['macd_dif'].ewm(span=9, adjust=False).mean()
            df['macd_hist'] = 2 * (df['macd_dif'] - df['macd_dea'])

            # KDJ
            low_list = df['low'].rolling(9).min()
            high_list = df['high'].rolling(9).max()
            rsv = (df['close'] - low_list) / (high_list - low_list) * 100
            df['kdj_k'] = rsv.ewm(com=2, adjust=False).mean()
            df['kdj_d'] = df['kdj_k'].ewm(com=2, adjust=False).mean()
            df['kdj_j'] = 3 * df['kdj_k'] - 2 * df['kdj_d']

            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))

            # 布林带
            df['boll_mid'] = df['close'].rolling(20).mean()
            std = df['close'].rolling(20).std()
            df['boll_upper'] = df['boll_mid'] + 2 * std
            df['boll_lower'] = df['boll_mid'] - 2 * std

            return df

        except Exception as e:
            print(f"⚠️ 计算技术指标失败: {e}")
            return df

    def _convert_to_tdx_format(self, symbol: str) -> str:
        """转换为通达信格式"""
        if symbol.startswith('0') or symbol.startswith('3'):
            return f"0.{symbol}"  # 深圳
        elif symbol.startswith('6'):
            return f"1.{symbol}"  # 上海
        else:
            return symbol

    def analyze_technical(self, symbol: str) -> Dict:
        """
        综合技术分析

        Args:
            symbol: 股票代码

        Returns:
            技术分析结果显示
        """
        result = {
            'symbol': symbol,
            'realtime': None,
            'kline_daily': None,
            'indicators': {},
            'support_resistance': {},
            'trend': '',
            'signal': ''
        }

        # 1. 获取实时行情
        try:
            result['realtime'] = self.get_realtime_quotes(symbol)
        except Exception as e:
            print(f"⚠️ 获取实时行情失败: {e}")
            raise Exception("无法获取实时行情，技术分析中止")

        # 2. 获取日K数据
        try:
            kline_data = self.get_kline_data(symbol, frequency='daily', offset=100)
            if kline_data is not None:
                result['kline_daily'] = kline_data.tail(10)  # 最近10天

                # 3. 分析技术指标
                latest = kline_data.iloc[-1]

                result['indicators'] = {
                    'macd_dif': round(float(latest.get('macd_dif', 0)), 3),
                    'macd_dea': round(float(latest.get('macd_dea', 0)), 3),
                    'macd_hist': round(float(latest.get('macd_hist', 0)), 3),
                    'kdj_k': round(float(latest.get('kdj_k', 0)), 2),
                    'kdj_d': round(float(latest.get('kdj_d', 0)), 2),
                    'kdj_j': round(float(latest.get('kdj_j', 0)), 2),
                    'rsi': round(float(latest.get('rsi', 0)), 2),
                    'boll_upper': round(float(latest.get('boll_upper', 0)), 2),
                    'boll_mid': round(float(latest.get('boll_mid', 0)), 2),
                    'boll_lower': round(float(latest.get('boll_lower', 0)), 2),
                }

                # 4. 支撑位和阻力位
                recent_high = kline_data['high'].tail(20).max()
                recent_low = kline_data['low'].tail(20).min()
                result['support_resistance'] = {
                    'resistance': round(float(recent_high), 2),
                    'support': round(float(recent_low), 2)
                }

                # 5. 趋势判断
                ma5 = kline_data['close'].tail(5).mean()
                ma20 = kline_data['close'].tail(20).mean()
                current_price = result['realtime']['price']

                if current_price > ma5 > ma20:
                    result['trend'] = '强势上涨'
                elif current_price > ma20:
                    result['trend'] = '温和上涨'
                elif current_price < ma20 < ma5:
                    result['trend'] = '弱势下跌'
                else:
                    result['trend'] = '震荡整理'

                # 6. 信号判断
                macd_hist = latest.get('macd_hist', 0)
                rsi = latest.get('rsi', 50)

                if macd_hist > 0 and rsi < 30:
                    result['signal'] = '强烈买入'
                elif macd_hist > 0 and rsi < 50:
                    result['signal'] = '买入'
                elif macd_hist < 0 and rsi > 70:
                    result['signal'] = '强烈卖出'
                elif macd_hist < 0 and rsi > 50:
                    result['signal'] = '卖出'
                else:
                    result['signal'] = '持有'

        except Exception as e:
            print(f"⚠️ 获取K线数据失败: {e}")
            raise Exception("无法获取K线数据，技术分析中止")

        return result


# ==================== 便捷函数 ====================

def integrate_technical_to_report(symbol: str, output_format: str = 'markdown') -> str:
    """
    将技术面分析整合到报告中

    Args:
        symbol: 股票代码
        output_format: 输出格式，'markdown' 或 'json'

    Returns:
        分析报告字符串，或JSON字典
    """
    try:
        analyzer = TechnicalAnalyzer()
        analysis = analyzer.analyze_technical(symbol)

        if output_format == 'markdown':
            realtime = analysis.get('realtime', {})
            indicators = analysis.get('indicators', {})
            support_res = analysis.get('support_resistance', {})

            md = f"""
## 技术面分析

### 实时行情
- **当前价格**: {realtime.get('price', 0):.2f} 元
- **涨跌幅**: {realtime.get('change_pct', 0):.2f}%
- **成交量**: {realtime.get('volume', 0):,} 手
- **成交额**: {realtime.get('amount', 0) / 100000000:.2f} 亿元
- **数据来源**: {realtime.get('source', 'unknown')}

### 技术指标
- **MACD**: DIF={indicators.get('macd_dif', 0)}, DEA={indicators.get('macd_dea', 0)}, HIST={indicators.get('macd_hist', 0)}
- **KDJ**: K={indicators.get('kdj_k', 0)}, D={indicators.get('kdj_d', 0)}, J={indicators.get('kdj_j', 0)}
- **RSI**: {indicators.get('rsi', 0)}
- **布林带**: 上轨={indicators.get('boll_upper', 0)}, 中轨={indicators.get('boll_mid', 0)}, 下轨={indicators.get('boll_lower', 0)}

### 支撑位/阻力位
- **阻力位**: {support_res.get('resistance', 0):.2f} 元
- **支撑位**: {support_res.get('support', 0):.2f} 元

### 趋势判断
- **当前趋势**: {analysis.get('trend', '未知')}
- **操作信号**: {analysis.get('signal', '未知')}
"""
            return md

        elif output_format == 'json':
            return analysis

        else:
            return analysis

    except Exception as e:
        print(f"❌ 整合技术面分析失败: {e}")
        return f"❌ 无法获取技术面数据: {e}"


# ==================== 测试代码 ====================

if __name__ == '__main__':
    print("=" * 60)
    print("测试 technical_analysis.py（完整版 - 集成代理+缓存+最优IP）")
    print("=" * 60)

    try:
        # 分析润泽科技
        print("\n正在分析润泽科技(300442)...")
        result = integrate_technical_to_report('300442', 'markdown')
        print(result)

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    print("\n使用说明：")
    print("1. 修改上方的配置区域（代理、延迟、缓存等）")
    print("2. 直接运行: python technical_analysis.py")
    print("3. 或在代码中使用：")
    print("   from technical_analysis import TechnicalAnalyzer")
    print("   analyzer = TechnicalAnalyzer()")
    print("   result = analyzer.analyze_technical('300442')")
