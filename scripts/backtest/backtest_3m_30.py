import os, time
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""

import akshare as ak

stocks_30 = {
    "半导体": [
        ("长电科技","600584"),("通富微电","002156"),("晶方科技","603005"),
        ("士兰微","600460"),("三安光电","600703"),("华天科技","002185"),
        ("至纯科技","603690"),("全志科技","300458"),("韦尔股份","603501"),
        ("兆易创新","603986")
    ],
    "电力": [
        ("长江电力","600900"),("华能国际","600011"),("国电电力","600795"),
        ("华电国际","600027"),("三峡能源","600905"),("京能电力","600578"),
        ("华光环能","600475"),("大唐发电","601991"),("中国核电","601985"),
        ("华能水电","600025")
    ],
    "算力": [
        ("中科曙光","603019"),("浪潮信息","000977"),("紫光股份","000938"),
        ("中兴通讯","000063"),("烽火通信","600498"),("中际旭创","300308"),
        ("新易盛","300502"),("天孚通信","300394"),("光迅科技","002281"),
        ("华工科技","000988")
    ]
}

all_results = []
failed = []

print("开始获取30只股票财务数据...")
print("=" * 70)

for sector, stock_list in stocks_30.items():
    for name, code in stock_list:
        try:
            df = ak.stock_financial_abstract_ths(symbol=code, indicator="按报告期")
            time.sleep(0.5)
            l = df.iloc[-1]
            
            def n(s):
                try: return float(str(s).replace("%",""))
                except: return 0.0
            def y(s):
                try:
                    s2 = str(s).replace("亿","")
                    if "万" in s2: return float(s2.replace("万","")) / 10000
                    return float(s2)
                except: return 0.0
            
            profit = y(l.get("净利润","0"))
            koufei = y(l.get("扣非净利润","0"))
            rev_yoy = n(l.get("营业总收入同比增长率","0"))
            profit_yoy = n(l.get("净利润同比增长率","0"))
            kf_ratio = (koufei / profit * 100) if profit != 0 else 0
            
            score = 0
            if rev_yoy > 15: score += 2
            if profit_yoy > 50 and kf_ratio > 60: score += 2
            elif profit_yoy > 50: score += 1
            
            all_results.append((score, sector, name, code, rev_yoy, profit_yoy, kf_ratio))
            
        except Exception as e:
            failed.append((name, code))
            time.sleep(0.5)

print(f"\n成功: {len(all_results)}只  失败: {len(failed)}只")
print("=" * 70)
print("v2.4修正评分: 营收同比>15%(2分)+净利同比>50%+扣非>60%(2分)+扣非占比>60%(1分)")
print("-" * 70)
print(f"{'股票':<8}{'板块':<6}{'评分':>4}{'营收同比':>8}{'净利同比':>8}{'扣非占比':>8}")
print("-" * 55)

for r in sorted(all_results, key=lambda x: x[0], reverse=True):
    print(f"{r[2]:<8}{r[1]:<6}{r[0]:>3}分 {r[4]:>6.1f}% {r[5]:>7.1f}% {r[6]:>6.0f}%")

print()
print("=" * 70)
print("板块统计")
print("-" * 70)
for sec in ["半导体","电力","算力"]:
    sr = [r for r in all_results if r[1]==sec]
    if sr:
        ss = [r[0] for r in sr]
        print(f"{sec:<8} {len(sr):>2}只  平均{sum(ss)/len(ss):.1f}分  最高{max(ss)}分  中位数{sorted(ss)[len(ss)//2]}分  >=3分{sum(1 for s in ss if s>=3)}只")
