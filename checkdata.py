import aiohttp
import os
import pandas as pd
import asyncio
from lxml import etree
from fuzzywuzzy import process

def area2code(area):
    path = os.path.split(os.path.realpath(__file__))[0]
    path = os.path.join(path,"货币代码.xls")
    df1 = pd.read_excel(path)
    index = df1['货币名称']
    df1 = df1.set_index('货币名称')
    area = process.extractOne(area,index)[0]
    code = df1.at[area,'货币代码']
    return code


async def queryhuilv(money1, money2, num = 100):
    money1 = area2code(money1)
    money2 = area2code(money2)
    # print(area1,area2)
    url = "https://qq.ip138.com/hl.asp"
    params = {"from":money1,"to":money2,"q":num}
    headers = headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    # Requests sorts cookies= alphabetically
    # 'Cookie': f"__bid_n=184460da2c46b2e1104207; FPTOKEN=30{KXY7LQklYEzhs2YmAbOiRnYp+21jKfPFshPbN2eXWwQeLkpSMLLvptQd/jekZhfPmvvO2IUH/wVuJAQv35IkIFKok4HFWRv41AQUExCKFTTztNZYpnkvGQhvNgdfZkRDZi/kw31kJWkchOttqxZlgRdrrs562E0TIU2tU8xB0rmNYyHMKGzHnZhzxw3RRDtGPSiK89DuANZdZ/beGA3sG2KiWVuvR0bqWBR52pXCCGadEAtMkihFqf1nwDECTAc7A5QedEySJYeEH68uNXGXRoBwa52dZYNSvpx5+4hBddzmsCj9RKbAEiVj+WKtlUcbGS1nUBGXIzkW8vG+KU6Zp33VXo60pyj/jciCoRA5UfegejjoLfP7Zmmmy9llV/5+|wbVZzUQA/tY4y/HfEChP14s7CB2Ab8u3kv9qsu3VUpI=|10|62a0d06eb92929ddb518111da24eceab;} ASPSESSIONIDCSDBSASS=BAEPFPDBLCFBENOBGPDLBDCA; Hm_lvt_ecdd6f3afaa488ece3938bcdbb89e8da=1667622609,1667622798,1667623687,1667649416; Hm_lpvt_ecdd6f3afaa488ece3938bcdbb89e8da=1667650302",
    'Pragma': 'no-cache',
    'Referer': 'https://qq.ip138.com/hl.asp?from=USD&to=CNY&q=100%20',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36 Edg/107.0.1418.35',
    'sec-ch-ua': '"Microsoft Edge";v="107", "Chromium";v="107", "Not=A?Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',}

    async with aiohttp.ClientSession() as session:
        async with session.get(url=url,params=params,headers=headers) as resp:
            response = await resp.text()
            tree = etree.HTML(response)
            money = tree.xpath("//tr[3]/td[3]/p/text()")[0]
            return money
            
 
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(queryhuilv("元","美元"))
    print(result)