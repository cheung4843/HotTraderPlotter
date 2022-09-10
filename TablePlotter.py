import datetime
import requests
import time
import pandas as pd
from bokeh.models import *
from bokeh.plotting import *
from bokeh.layouts import *
from bokeh.io import *


def to_datetime(time_stamp: int):
    struct_time = time.localtime(time_stamp / 1000)  # 因為只能有10位，故除1000
    time_string = time.strftime("%Y-%m-%d %H:%M:%S", struct_time)  # 轉成字串
    return time_string


#################
# API取幣價資料
#################
def crypto_candles(start_time, end_time, t_symbol='BTCUSDT'):
    BASE_URL = 'https://api.binance.com'
    kline = '/api/v1/klines'

    symbol = t_symbol
    interval = '1h'
    start = f'{start_time} 00:00:01'
    end = f'{end_time} 00:00:00'
    startTime = str(int(time.mktime(time.strptime(start, "%Y-%m-%d %H:%M:%S"))))
    endTime = str(int(time.mktime(time.strptime(end, "%Y-%m-%d %H:%M:%S"))))

    Hour_gap = (int(endTime) - int(startTime)) / 60 / 60
    relayStartTime = int(startTime)
    total_data = []
    while Hour_gap > 500:
        relayEndTime = relayStartTime + 499 * 60 * 60
        Hour_gap -= 500
        inStart = str(int(relayStartTime))
        inEnd = str(int(relayEndTime))
        input = BASE_URL + kline + '?' + 'symbol=' + symbol + '&interval=' + interval + '&startTime=' + inStart + '000' + '&endTime=' + inEnd + '000'

        relayStartTime = relayEndTime + 1 * 60 * 60
        total_data += requests.get(input).json()

    inStart = str(int(relayStartTime))
    inEnd = str(int(endTime))
    input = BASE_URL + kline + '?' + 'symbol=' + symbol + '&interval=' + interval + '&startTime=' + inStart + '000' + '&endTime=' + inEnd + '000'
    tmp_data = requests.get(input).json()
    total_data += tmp_data
    data = total_data

    print(f'api共傳{len(data)}筆')

    open_p, close_p, high_p, low_p, time_p = [], [], [], [], []

    for candle in data:
        open_p.append(float(candle[1]))
        high_p.append(float(candle[2]))
        low_p.append(float(candle[3]))
        close_p.append(float(candle[4]))
        time_p.append(to_datetime(candle[0]))

    raw_data = {
        'Date': pd.DatetimeIndex(time_p),
        'Open': open_p,
        'High': high_p,
        'Low': low_p,
        'Close': close_p
    }
    _df = pd.DataFrame(raw_data)

    return _df


#################
# 交易員的圖
#################
print('hi')
t_df = pd.read_table(
    'TestData.txt', header=None, sep="\t", engine='python')
t_df.columns = ["ID", "Name", "Gearing", "LongORShort", "Open", "Close", "OpenTime", "CloseTime", "ProfitRate"]

# 想要的交易員ID
id_filter = t_df["ID"] == 747621985767161859
sel_df = t_df[id_filter]
sel_df.reset_index(inplace=True, drop=True)

# 做空做多數字轉換成字串
sel_df["LongORShort"] = sel_df["LongORShort"].map(lambda x: "做多" if str(x) == '1' else "做空")

# 把交易員的英國+0時間轉成台灣+8時間
open_hour_interval = []
close_hour_interval = []
for i in range(len(sel_df)):
    open_time = sel_df.loc[i, 'OpenTime']
    close_time = sel_df.loc[i, 'CloseTime']
    datetime_open_time = datetime.datetime.strptime(open_time, '%Y-%m-%d %H:%M:%S') + datetime.timedelta(
        hours=8)
    datetime_close_time = datetime.datetime.strptime(close_time, '%Y-%m-%d %H:%M:%S') + datetime.timedelta(
        hours=8)
    str_open_time = datetime.datetime.strftime(datetime_open_time, '%Y-%m-%d %H:%M:%S')
    str_close_time = datetime.datetime.strftime(datetime_close_time, '%Y-%m-%d %H:%M:%S')
    sel_df.loc[i, 'OpenTime'] = str_open_time
    sel_df.loc[i, 'CloseTime'] = str_close_time
    open_hour_interval.append(f'{str_open_time.split(" ")[0]} {str_open_time.split(" ")[1].split(":")[0]}:00:00')
    close_hour_interval.append(f'{str_close_time.split(" ")[0]} {str_close_time.split(" ")[1].split(":")[0]}:00:00')

# 新增只有小時區隔的行，有警告但先忽略
sel_df['open_hour_interval'] = pd.DatetimeIndex(open_hour_interval)
sel_df['close_hour_interval'] = pd.DatetimeIndex(close_hour_interval)

# 最早開倉時間的當天00:00
start_time = datetime.datetime.strptime(sel_df['OpenTime'][0].split(" ")[0], "%Y-%m-%d")
# 最晚平倉時間的明天00:00
end_time = datetime.datetime.strptime(sel_df['CloseTime'][len(sel_df) - 1].split(" ")[0],
                                      "%Y-%m-%d") + datetime.timedelta(
    days=1)
print(f'畫圖開始時間:{start_time}, 結束時間:{end_time}')
df = crypto_candles(datetime.datetime.strftime(start_time, '%Y-%m-%d'),
                    datetime.datetime.strftime(end_time, '%Y-%m-%d'))
#################
# k線圖
#################

source = ColumnDataSource(data=df)
# print(df.info())
inc_b = source.data['Close'] > source.data['Open']
inc = CDSView(source=source, filters=[BooleanFilter(inc_b)])
dec_b = source.data['Open'] > source.data['Close']
dec = CDSView(source=source, filters=[BooleanFilter(dec_b)])
w = 86400 * 20
p = figure(x_axis_type="datetime", sizing_mode="stretch_width", height=400,
           tools=["pan,zoom_in,zoom_out,crosshair,reset,save,wheel_zoom", ], toolbar_location="above",
           y_axis_label="price", x_axis_label="time")
segment = p.segment(source=source, x0='Date', x1='Date', y0='High', y1='Low', color="blue")

inc_vbar = p.vbar(source=source, view=inc, x='Date', width=w, top='Open', bottom='Close', fill_color="#25a69a",
                  line_color="#25a69a", alpha=1, muted_alpha=0.8, legend_label='inc')
dec_vbar = p.vbar(source=source, view=dec, x='Date', width=w, top='Open', bottom='Close', fill_color="#ee534f",
                  line_color="#ee534f",
                  alpha=1, muted_alpha=0.8, legend_label='dec')

# 刪除ID行
sel_df = sel_df.drop(['ID'], axis=1)

# 滾輪放大自動開啟
p.toolbar.active_scroll = p.select_one(WheelZoomTool)
# 隱藏工具欄
p.toolbar_location = None

# 產生顏色
colors = ['white' if sel_df.loc[i, 'LongORShort'] == '做空' else '#25a69a' for i in range(len(sel_df))]
sel_df['color'] = colors

t_source = ColumnDataSource(data=sel_df)
# 開倉時間的點
open_dot = p.triangle(source=t_source, x='open_hour_interval', y='Open', color='color', size=10)
# 平倉時間的點
close_dot = p.circle(source=t_source, x='close_hour_interval', y='Close', color='color', size=10)

# 按標籤加深bar的顏色
p.legend.click_policy = "mute"

# 交易員的hover
p.add_tools(HoverTool(
    renderers=[open_dot, close_dot],
    tooltips=[
        ("#編號", "$index"),
        ('槓桿', '@Gearing'),
        ('操作', '@LongORShort'),
        ('開倉價', '@Open{0.00}'),
        ('平倉價', '@Close{0.00}'),
        ('開倉時間', '@OpenTime{%Y-%m-%d %H:%M:%S}'),
        ('平倉時間', '@CloseTime{%Y-%m-%d %H:%M:%S}'),
        ('收益率', '@ProfitRate{0.00}%'),
    ],

    formatters={
        '@OpenTime': 'datetime',
        '@CloseTime': 'datetime'
    },
    mode='mouse'
))
# 表格
template1 = """                
            <span style="color:<%= 
                (function getColor(){
                    if (LongORShort == "做多")
                        {return('green')}
                    else if (LongORShort == "做空")
                        {return('red')}
                    else 
                        {return('blue')}
                    }()) %>;"> 
                <%= value %>
            </span>
            """
template2 = """                
            <span style="color:<%= 
                (function getColor(){
                    if (ProfitRate > 0)
                        {return('green')}
                    else if (ProfitRate == 0)
                        {return('blue')}
                    else 
                        {return('red')}
                    }()) %>;"> 
                <%= value %>
            </span>
            """
formatter1 = HTMLTemplateFormatter(template=template1)
formatter2 = HTMLTemplateFormatter(template=template2)
columns = [
    TableColumn(field="Gearing", title="槓桿"),
    TableColumn(field="LongORShort", title="操作", formatter=formatter1),
    TableColumn(field="OpenTime", title="開倉時間"),
    TableColumn(field="Open", title="開倉價"),
    TableColumn(field="CloseTime", title="平倉時間"),
    TableColumn(field="Close", title="平倉價"),
    TableColumn(field="ProfitRate", title="收益率(%)", formatter=formatter2),
]
data_table = DataTable(source=t_source, columns=columns, sizing_mode="stretch_width", selectable=True, sortable=True,
                       autosize_mode="fit_viewport")
output_file("TablePlotter.html")
curdoc().theme = 'contrast'
show(column(p, data_table))
####################
