import os
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""
os.environ["http_proxy"] = ""
os.environ["https_proxy"] = ""

import requests, json

# 用新浪K线API获取3个月数据
stock_list = [("京能电力","600578","sh"),("大唐发电","601991","sh"),("全志科技","300458","sz")]

for name, code, pre in stock_list:
    try:
        url = f"https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketData.getKLineData?symbol={pre}{code}&scale=240&ma=no&datalen=60"
        r = requests.get(url, timeout=10, headers={"User-Agent":"Mozilla/5.0"})
        if r.status_code == 200 and len(r.text) > 50:
            data = json.loads(r.text)
            first_c = float(data[0]["close"])
            last_c = float(data[-1]["close"])
            chg = (last_c - first_c) / first_c * 100
            print(f"{name:<8} {code:<8} 首{first_c:.2f}→末{last_c:.2f}  {chg:+.1f}%")
        else:
            print(f"{name:<8} {code:<8} HTTP{r.status_code}")
    except Exception as e:
        print(f"{name:<8} {code:<8} ❌ {str(e)[:40]}")
