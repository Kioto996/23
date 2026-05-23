import akshare as ak, time

stocks = {
    '半导体':{'长电科技':'600584','通富微电':'002156','晶方科技':'603005',
              '士兰微':'600460','三安光电':'600703','华天科技':'002185',
              '至纯科技':'603690','全志科技':'300458'},
    '电力':{'长江电力':'600900','华能国际':'600011','国电电力':'600795',
            '华电国际':'600027','三峡能源':'600905','京能电力':'600578',
            '华光环能':'600475','大唐发电':'601991'}
}

print("修正验证：营收同比>15%代替环比")
print("="*70)
for sector, stock_list in stocks.items():
    for name, code in stock_list.items():
        try:
            df = ak.stock_financial_abstract_ths(symbol=code, indicator='按报告期')
            time.sleep(0.4)
            l = df.iloc[-1]
            rev_yoy_s = l.get('营业总收入同比增长率','0')
            profit_yoy_s = l.get('净利润同比增长率','0')
            profit_s = str(l.get('净利润','0'))
            koufei_s = str(l.get('扣非净利润','0'))
            
            rev_yoy = 0.0
            try:
                rev_yoy = float(str(rev_yoy_s).replace('%',''))
            except:
                pass
            
            profit_yoy = 0.0
            try:
                profit_yoy = float(str(profit_yoy_s).replace('%',''))
            except:
                pass
            
            kf_ratio = 0.0
            try:
                p = float(profit_s.replace('亿',''))
                k = float(koufei_s.replace('亿',''))
                if p != 0:
                    kf_ratio = k / p * 100
            except:
                pass
            
            # 评分
            score = 0
            if rev_yoy > 15: score += 2
            if profit_yoy > 50: score += 2
            if kf_ratio > 60: score += 1
            
            rev_str = str(rev_yoy_s)[:8]
            profit_str = str(profit_yoy_s)[:8]
            
            print(f"{name:<8} 营收同比{rev_str:>8} 净利同比{profit_str:>8} 扣非占比{kf_ratio:>5.0f}%  评分{score}分/5")
        except Exception as e:
            print(f"{name:<8} 失败: {str(e)[:40]}")
            time.sleep(0.4)

print()
print("核心发现：营收环比>15% → 应改为营收同比>15%")
print("Q1季节性导致所有16只环比都不达标，改成同比后逻辑正确")
