import os
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""
os.environ["http_proxy"] = ""
os.environ["https_proxy"] = ""

import akshare as ak, time, requests, json

# 从之前30只回测的主板股里找 业绩好+没涨太多 的
stocks = [
    ("华天科技","002185","sz"),  # 深主板, 净利+568%, 3月+14%
    ("通富微电","002156","sz"),  # 深主板, 净利+224%, 3月+21%
    ("士兰微","600460","sh"),    # 沪主板, 净利+40%, 3月+15%
    ("长电科技","600584","sh"),  # 沪主板, 净利+42%, 已涨+30%
    ("紫光股份","000938","sz"),  # 深主板, 净利+126%, 已涨+30%
    ("华工科技","000988","sz"),  # 深主板, 净利+55%, 已涨+79%
    ("中科曙光","603019","sh"),  # 沪主板, 净利+22%, 已涨+8%
    ("烽火通信","600498","sh"),  # 沪主板, 净利-30%
]

print("主板候选: 业绩好+没涨太多的")
for name, code, mkt in stocks:
    # 3月涨幅
    url = f"https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketData.getKLineData?symbol={mkt}{code}&scale=240&ma=no&datalen=65"
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent":"Mozilla/5.0"})
        data = json.loads(r.text)
        fc = float(data[0]["close"])
        lc = float(data[-1]["close"])
        chg = (lc-fc)/fc*100
        low3m = min(float(d["low"]) for d in data)
        high3m = max(float(d["high"]) for d in data)
        pos = (lc-low3m)/(high3m-low3m)*100
    except:
        chg, pos = 0, 0
    
    print(f"{name:<8} {code:<8} 现价{lc:>6.2f}  3月{chg:>+5.1f}%  位置{pos:>4.0f}%分位")
