import json
from hoshino import Service, priv
from hoshino.util import FreqLimiter
import os
import re
from .checkdata import queryhuilv

flmt = FreqLimiter(5)

sv = Service(
    name='汇率数据',  # 功能名
    use_priv=priv.NORMAL,  # 使用权限
    manage_priv=priv.ADMIN,  # 管理权限
    visible=True,  # False隐藏
    enable_on_default=True,  # 是否默认启用
)

# ============================================ #

def load_config():#加载config
    filename = os.path.join(os.path.dirname(__file__), '汇率定义.json')
    with open(filename, encoding='utf8') as f:
        config = json.load(f)
        return config 

def doreplace(money):#货币名称替换
    config = load_config()#每个函数使用前最好加载一下config，以防使用旧数据
    if money in config:
        money = config[money][1]
    return money

def numreplace(num,money1,money2):
    config = load_config()
    if money1 in config:
        num = float(num)*float(config[money1][0])
    elif money2 in config:
        num = float(num)/float(config[money2][0])
    return num

async def get_huilv_data(money1_orginal, num_orginal = 100, money2_orginal = "人民币"):
    num = numreplace(num_orginal,money1_orginal,money2_orginal)#等效金额
    money1 = doreplace(money1_orginal)
    money2 = doreplace(money2_orginal)
    try:
        money1 = await queryhuilv(money1,money2,num)
        msg = f"{num_orginal}{money1_orginal}可以兑换{money1}{money2_orginal}哦"
    except:
        msg = f"没有查询到{money1_orginal}汇率哦，如果你没搞错的话请通过“汇率定义”来告诉我这个币的价值。"
    return msg

@sv.on_suffix("汇率")
@sv.on_prefix("汇率")
async def huilv_simple(bot, ev):
    # 冷却器检查
    if not flmt.check(ev['user_id']):
        await bot.send(ev, f"查询冷却中，请{flmt.left_time(ev['user_id']):.2f}秒后再试~", at_sender=True)
        return
    money = ev.raw_message.replace("汇率","")
    msg = await get_huilv_data(money)
    flmt.start_cd(ev['user_id'])
    await bot.send(ev, msg)

@sv.on_rex(r'((?P<num>\d+(?:\.\d+)?)|(?:.*))(?P<keyword>.*?)[可][以](兑换|[换])[多][少](?P<keyword2>.*?)$')
async def huilv_hard(bot, ev):
    # 冷却器检查
    if not flmt.check(ev['user_id']):
        await bot.send(ev, f"查询冷却中，请{flmt.left_time(ev['user_id']):.2f}秒后再试~", at_sender=True)
        return
    money = ev['match'].group('keyword')
    money2 = ev['match'].group('keyword2')
    num = ev['match'].group('num')
    msg = await get_huilv_data(money,num,money2)
    flmt.start_cd(ev['user_id'])
    await bot.send(ev, msg)

@sv.on_fullmatch('汇率帮助')
async def huilv_help(bot, ev):
    help_msg = "输入xx汇率.输入XX美元可以换多少人民币.输入XX人民币可以换多少美元"
    await bot.send(ev, help_msg)

@sv.on_prefix('汇率定义','汇率设置')
async def huilv_define(bot, ev):
    config = load_config()
    help = "请按照格式（汇率定义 【数字】新币种 【数字】另外一种币）"
    info = ev.raw_message#获取行信息
    content = info.split()#按空格拆分数据，形成字典
    lenC = len(content)
    if lenC != 3:#校验是否为三段数据，不是三段说明错误
        await bot.send(ev, help)
    else:
        if re.match(r"[1-9]\d*\.\d+|^0\.\d+|^[1-9]\d*|^0[\u4e00-\u9fa5]{0,5}",content[1]):#[1-9]\d*\.\d+|^0\.\d+|^[1-9]\d*|^0为浮点数正则，要支持0，非零整数，0开头的浮点型，非0开头的浮点型
            content[1] = re.match(r"([1-9]\d*\.\d+|^0\.\d+|^[1-9]\d*|^0)([\u4e00-\u9fa5]{0,5})",content[1])#[\u4e00-\u9fa5]识别中文
            num1 = content[1].group(1)
            new_money = content[1].group(2)
            if re.match(r"[1-9]\d*\.\d+|^0\.\d+|^[1-9]\d*|^0[\u4e00-\u9fa5]{0,5}",content[2]):
                content[2] = re.match(r"([1-9]\d*\.\d+|^0\.\d+|^[1-9]\d*|^0)([\u4e00-\u9fa5]{0,5})",content[2])
                num2 = content[2].group(1)
                old_money = content[2].group(2)
                if old_money in config:#先看看是不是在config
                    num2 = float(num2)*float(config[old_money][0])#等效金额
                    old_money = config[old_money][1]#替换为原本货币，防止出现嵌套，1环奈币等于10小明币，1小明币等于3.14公主币这种情况
                else :
                    check = await get_huilv_data(old_money)
                    if "没有查询到" in check:#验证是不是已存在货币
                        await bot.send(ev, "第二个货币我也不认识")
                        return
                num_final = float(num2)/float(num1)#计算出1个换多少
                config[new_money] = [num_final,old_money]
                config_file = os.path.join(os.path.dirname(__file__), '汇率定义.json')
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False)
                await bot.send(ev, "设置成功")
            else: 
                await bot.send(ev, help)  
        else: 
            await bot.send(ev, help)

@sv.on_prefix('取消定义汇率')
async def huilv_delete(bot, ev):
    info = ev.raw_message
    content = info.split()
    if len(content) == 2:
        config = load_config()
        try:
            config.pop(content[1])
            config_file = os.path.join(os.path.dirname(__file__), '汇率定义.json')
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False)
            await bot.send(ev, "取消成功")
        except:
           await bot.send(ev, "取消失败") 
    else:
        await bot.send(ev, "你多输入了参数,爬爬")