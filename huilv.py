import json
from hoshino import Service, priv
import aiohttp
from hoshino.util import FreqLimiter
from PIL import Image, ImageDraw, ImageFont
import io
import os
import base64
from lxml import etree
import re

url = "https://www.usd-cny.com/"  
flmt = FreqLimiter(5)

sv = Service(
    name='汇率数据',  # 功能名
    use_priv=priv.NORMAL,  # 使用权限
    manage_priv=priv.ADMIN,  # 管理权限
    visible=True,  # False隐藏
    enable_on_default=True,  # 是否默认启用
)


# ============================================ #
async def fetch(session, url):
    async with session.get(url) as response:
        return await response.text(encoding='gbk')  # 需要json则改这里，或者移到下面

def load_config(inbuilt_file_var):#加载config
    filename = os.path.join(os.path.dirname(inbuilt_file_var), '汇率定义.json')
    with open(filename, encoding='utf8') as f:
        config = json.load(f)
        return config 

def doreplace(area):#货币名称替换
    config = load_config(__file__)#每个函数使用前最好加载一下config，以防使用旧数据
    if area in config:
        area = config[area][1]
    return area

def numreplace(num,area,area2):#等效金额计算，之前只是名称改变，本质上是1换1，但是自定义汇率之后不仅要改变名称，还有根据汇率算出等效金额
    config = load_config(__file__)
    if area in config and area2 in config:
        num = float(num)*float(config[area][0])/float(config[area2][0])
    elif area in config:
        num = float(num)*float(config[area][0])
    elif area2 in config:
        num = float(num)/float(config[area2][0])
    return num

async def get_huilv_data_hard(area_orginal,num1,area2_orginal):
    num = numreplace(num1,area_orginal,area2_orginal)#等效金额
    area = doreplace(area_orginal)
    area2 = doreplace(area2_orginal)
    msg = ""
    dict = {}
    async with aiohttp.ClientSession() as session:  # 声明session为协程类
        html = await fetch(session, url=url)
        tree = etree.HTML(html)
    title = tree.xpath("/html/body/section/div/div/article/table//tr/td/a/text()")
    money = tree.xpath("/html/body/section/div/div/article/table//tr/td[2]/text()")
    for i in range(len(title)):
        dict[title[i]] = money[i]
    dict["人民币"] = "100"
    try:
        money = float(dict[area])/float(dict[area2])*float(num)
        money = "{:.2f}".format(money)
        msg = f"{num1}{area_orginal}可以兑换{money}{area2_orginal}哦"
    except:
        msg = f"没有查询到{area_orginal}汇率哦"#发现你之前竟然输出直接用替换好的名称    
    return msg

async def get_huilv_data(area_orginal: str) -> str:
    define_huilv = 1
    config = load_config(__file__)
    if area_orginal in config:#这里不要忘写替换，这个功能之前竟然没有名称替换
        area = config[area_orginal][1]
        define_huilv = config[area_orginal][0]
    else:
        area = area_orginal
    msg = ""
    dict = {}
    async with aiohttp.ClientSession() as session:  # 声明session为协程类
        html = await fetch(session, url=url)
        tree = etree.HTML(html)
    title = tree.xpath("/html/body/section/div/div/article/table//tr/td/a/text()")
    money = tree.xpath("/html/body/section/div/div/article/table//tr/td[2]/text()")
    for i in range(len(title)):
        dict[title[i]] = money[i]
    try:
        num_final = float(dict[area])*float(define_huilv)
        msg = f"{num_final}元人民币可以兑换100{area_orginal}哦"
    except:
        msg = f"没有查询到{area_orginal}汇率哦"
    return msg

def image_draw(msg):#除了报错，基本上用不上这个
    fontpath = font_path = os.path.join(os.path.dirname(__file__), 'simhei.ttf')
    font1 = ImageFont.truetype(fontpath, 16)
    width, height = font1.getsize_multiline(msg.strip())
    img = Image.new("RGB", (width + 20, height + 20), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), msg, fill=(0, 0, 0), font=font1)
    b_io = io.BytesIO()
    img.save(b_io, format="JPEG")
    base64_str = 'base64://' + base64.b64encode(b_io.getvalue()).decode()
    return base64_str

@sv.on_suffix("汇率") #rex效率低，不提倡
async def huilv_simple(bot, ev):
    # 冷却器检查
    if not flmt.check(ev['user_id']):
        await bot.send(ev, f"查询冷却中，请{flmt.left_time(ev['user_id']):.2f}秒后再试~", at_sender=True)
        return
    area = ev.raw_message.replace("汇率","")
    try:
        msg = await get_huilv_data(area)
        flmt.start_cd(ev['user_id'])
    except Exception as e:
        if str(e) == "'name'":
            msg = "无法查询该汇率"
        else:
            msg = f"查询{area}数据失败：{e}，如果你没搞错的话请通过“汇率定义”来告诉我这个币的价值"
            repr(e)
        flmt.start_cd(ev['user_id'], 3)
    if len(msg) < 30:
        await bot.send(ev, msg)
    else:
        pic = image_draw(msg)
        await bot.send(ev, f'[CQ:image,file={pic}]')

@sv.on_rex(r'((?P<num>\d+(?:\.\d+)?)|(?:.*))(?P<keyword>.*?)[可][以](兑换|[换])[多][少](?P<keyword2>.*?)$')
async def huilv_hard(bot, ev):
    # 冷却器检查
    if not flmt.check(ev['user_id']):
        await bot.send(ev, f"查询冷却中，请{flmt.left_time(ev['user_id']):.2f}秒后再试~", at_sender=True)
        return
    area = ev['match'].group('keyword')
    area2 = ev['match'].group('keyword2')
    num = ev['match'].group('num')
    try:
        msg = await get_huilv_data_hard(area,num,area2)
        flmt.start_cd(ev['user_id'])
    except Exception as e:
        if str(e) == "'name'":
            msg = "无法查询该地区汇率"
        else:
            msg = f"查询{area}数据失败：{e}"
            repr(e)
        flmt.start_cd(ev['user_id'], 3)
    if len(msg) < 30:
        await bot.send(ev, msg)
    else:
        pic = image_draw(msg)
        await bot.send(ev, f'[CQ:image,file={pic}]')

@sv.on_fullmatch('汇率帮助')
async def huilv_help(bot, ev):
    help_msg = '''【xx汇率】可以查询多少软妹币能换100个xx
                【（数字）（货币种类1）可以换多少（货币种类2）】两种货币金额转换
                【汇率定义 （数字+自定义货币）（数字+已有货币】
                【取消定义汇率 （已有货币）】'''
    await bot.send(ev, help_msg)

@sv.on_prefix('汇率定义','汇率设置')
async def huilv_define(bot, ev):
    config = load_config(__file__)
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
                    if check == f"没有查询到{old_money}汇率哦":#验证是不是已存在货币
                        await bot.send(ev, "第二个货币环奈也不认识")
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
        config = load_config(__file__)
        try:
            config.pop(content[1])
            config_file = os.path.join(os.path.dirname(__file__), '汇率定义.json')
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False)
            await bot.send(ev, "取消成功")
        except:
           await bot.send(ev, "取消失败") 
    else:
        await bot.send(ev, "你多输入了参数")