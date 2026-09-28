#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""由 quarterly.json 生成自包含 ECharts 页面 pig_cycle.html"""
import json, os

BASE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(BASE, 'data/pig_cycle/quarterly.json'), encoding='utf-8'))

labels = [d['label'] for d in D]
sows = [d.get('sows') for d in D]
pork = [d.get('pork_price') for d in D]
idx = [d.get('index_930707') for d in D]
my = [d.get('牧原股份') for d in D]
ws = [d.get('温氏股份') for d in D]


def norm(series):
    """以首个非空值=100 归一化"""
    base = next((v for v in series if v), None)
    return [round(v / base * 100, 1) if v else None for v in series]


# 存栏按季度重采样（Q4=年末值, 2025 有季度值）→ 用于归一化
sows_norm = norm(sows)

# 存栏粒度说明
gran_map = {}
for d in D:
    if d.get('sows'):
        g = {'year-end': '年末值', 'quarter': '季度值', 'month': '月度值'}.get(d.get('sows_granularity'), '')
        gran_map[d['label']] = g

# 元数据
meta = {
    'generatedAt': __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M'),
    'rows': len(D),
}

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>猪周期五指标季度对照 2018-2026</title>
<script src="lib/echarts.min.js"></script>
<style>
  :root{{--bg:#0a1930;--card:#102a4c;--card2:#143459;--gold:#d4a843;--gold2:#f0c96a;
        --txt:#e8eef7;--dim:#8fa8c8;--line:#1e4270;}}
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:var(--bg);color:var(--txt);font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;
       padding:18px;line-height:1.6}}
  .wrap{{max-width:1180px;margin:0 auto}}
  h1{{font-size:21px;color:var(--gold);font-weight:700;letter-spacing:.5px}}
  h1 small{{display:block;font-size:12px;color:var(--dim);font-weight:400;margin-top:5px;letter-spacing:0}}
  .card{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;margin-top:16px;
        box-shadow:0 4px 18px rgba(0,0,0,.25)}}
  .card h2{{font-size:15px;color:var(--gold2);margin-bottom:4px;font-weight:600}}
  .card .sub{{font-size:11.5px;color:var(--dim);margin-bottom:12px}}
  .chart{{width:100%;height:420px}}
  .chart.tall{{height:470px}}
  table{{width:100%;border-collapse:collapse;font-size:12px;font-variant-numeric:tabular-nums}}
  th,td{{padding:6px 8px;text-align:right;border-bottom:1px solid var(--line)}}
  th{{color:var(--gold2);font-weight:600;background:var(--card2);position:sticky;top:0;font-size:11.5px}}
  td:first-child,th:first-child{{text-align:left}}
  tbody tr:hover{{background:var(--card2)}}
  .tag{{display:inline-block;font-size:10px;padding:1px 5px;border-radius:3px;background:#1e4270;color:var(--dim);margin-left:4px}}
  .note{{font-size:11.5px;color:var(--dim);background:var(--card2);border-left:3px solid var(--gold);
        padding:10px 12px;border-radius:6px;margin-top:12px}}
  .note b{{color:var(--gold2)}}
  .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:10px;margin-top:6px}}
  .kpi{{background:var(--card2);border-radius:9px;padding:11px 13px;border-left:3px solid var(--gold)}}
  .kpi .k{{font-size:11px;color:var(--dim)}}
  .kpi .v{{font-size:19px;font-weight:700;color:var(--gold2);font-variant-numeric:tabular-nums}}
  .kpi .d{{font-size:11px;color:var(--dim)}}
  .scroll{{max-height:480px;overflow-y:auto}}
  footer{{text-align:center;color:var(--dim);font-size:11px;margin:20px 0 8px}}
</style>
</head>
<body>
<div class="wrap">
  <h1>猪周期五指标季度对照（2018Q1 → 2026Q3）
    <small>能繁母猪存栏 · 猪肉价格 · 中证畜牧养殖指数(930707) · 牧原股份(002714) · 温氏股份(300498)
    ｜ 生成 {meta['generatedAt']} ｜ {meta['rows']} 个季度</small>
  </h1>

  <div class="card">
    <h2>① 归一化对照（各自起始=100，看涨跌节奏是否同步）</h2>
    <div class="sub">把五个量纲不同的指标拉平到同一起点，直接对比"谁先动、谁后动"</div>
    <div id="c1" class="chart tall"></div>
  </div>

  <div class="card">
    <h2>② 核心：能繁母猪存栏 vs 猪肉价格</h2>
    <div class="sub">能繁母猪是"十个月后的猪肉供给"，理论上领先猪价约 10 个月（约 3 个季度）</div>
    <div id="c2" class="chart"></div>
    <div class="note">
      <b>口径说明（重要）：</b>能繁母猪存栏仅 <b>{sum(1 for s in sows if s)}/35</b> 个季度有官方公布值 ——
      2018–2024 为<b>年末值</b>，2025 为<b>季度值</b>，2025Q4 取自 10 月<b>月度值</b>；<b>2026 年暂无公开数据</b>。
      线条在无数据季度按相邻已公布值连接（不插值、不编造）。其余四条指标均为完整季度值。
    </div>
  </div>

  <div class="card">
    <h2>③ 畜牧指数与猪企股价（归一化）</h2>
    <div class="sub">指数反映板块整体，牧原/温氏反映龙头个股——看市场如何提前反映周期</div>
    <div id="c3" class="chart"></div>
  </div>

  <div class="card">
    <h2>④ 关键读数</h2>
    <div class="grid" id="kpi"></div>
  </div>

  <div class="card">
    <h2>⑤ 季度数据明细（真实值，可核对）</h2>
    <div class="sub">存栏单位：万头；猪价单位：元/公斤（季末）；股价为前复权收盘价</div>
    <div class="scroll"><table id="tbl"></table></div>
  </div>

  <footer>
    数据源：能繁母猪存栏—农业农村部（经玄田数据/中国养猪网整理）；猪肉价格—生猪现货成交均价（周频，取季末值）；
    中证畜牧养殖指数—中证指数有限公司官网；股价—新浪财经（前复权）。<br>
    仅作复盘研究，不构成投资建议。
  </footer>
</div>

<script>
const L = {json.dumps(labels, ensure_ascii=False)};
const SOWS = {json.dumps(sows)};
const PORK = {json.dumps(pork)};
const IDX  = {json.dumps(idx)};
const MY   = {json.dumps(my)};
const WS   = {json.dumps(ws)};
const SOWS_N = {json.dumps(sows_norm)};
const IDX_N  = {json.dumps(norm(idx))};
const MY_N   = {json.dumps(norm(my))};
const WS_N   = {json.dumps(norm(ws))};
const PORK_N = {json.dumps(norm(pork))};
const GRAN = {json.dumps(gran_map, ensure_ascii=False)};

const GOLD='#d4a843', ORANGE='#e8834a', BLUE='#4a9be8', GREEN='#3fbf8f', PURPLE='#a97be0', RED='#e05c5c';
const AX = {{axisLine:{{lineStyle:{{color:'#2a5580'}}}},axisLabel:{{color:'#8fa8c8',fontSize:11}},
             splitLine:{{lineStyle:{{color:'#163254',type:'dashed'}}}}}};

function base(extra){{
  return Object.assign({{
    backgroundColor:'transparent',
    tooltip:{{trigger:'axis',backgroundColor:'#0d2440',borderColor:GOLD,borderWidth:1,
             textStyle:{{color:'#e8eef7',fontSize:12}},axisPointer:{{type:'cross',crossStyle:{{color:GOLD}}}}}},
    legend:{{textStyle:{{color:'#8fa8c8',fontSize:12}},top:2,itemWidth:16,itemHeight:8}},
    grid:{{left:52,right:52,top:44,bottom:34}},
    xAxis:Object.assign({{type:'category',data:L,boundaryGap:false}},AX)
  }}, extra);
}}

// ① 归一化
echarts.init(document.getElementById('c1')).setOption(base({{
  legend:{{data:['能繁母猪存栏','猪肉价格','中证畜牧指数','牧原股份','温氏股份'],
          textStyle:{{color:'#8fa8c8',fontSize:12}},top:2,itemWidth:16,itemHeight:8}},
  yAxis:Object.assign({{type:'value',name:'指数(起点=100)',nameTextStyle:{{color:'#8fa8c8',fontSize:11}}}},AX),
  series:[
    {{name:'能繁母猪存栏',type:'line',data:SOWS_N,smooth:true,connectNulls:true,symbol:'circle',symbolSize:6,
      lineStyle:{{width:2.5,color:GOLD}},itemStyle:{{color:GOLD}},
      markPoint:{{symbolSize:44,label:{{fontSize:10,color:'#0a1930'}},data:[{{type:'max',name:'最高'}},{{type:'min',name:'最低'}}]}}}},
    {{name:'猪肉价格',type:'line',data:PORK_N,smooth:true,symbol:'none',lineStyle:{{width:2.5,color:ORANGE}}}},
    {{name:'中证畜牧指数',type:'line',data:IDX_N,smooth:true,symbol:'none',lineStyle:{{width:2,color:BLUE}}}},
    {{name:'牧原股份',type:'line',data:MY_N,smooth:true,symbol:'none',lineStyle:{{width:2,color:GREEN}}}},
    {{name:'温氏股份',type:'line',data:WS_N,smooth:true,symbol:'none',lineStyle:{{width:2,color:PURPLE}}}}
  ]
}}));

// ② 存栏 vs 猪价（双轴）
echarts.init(document.getElementById('c2')).setOption(base({{
  legend:{{data:['能繁母猪存栏(万头)','猪肉价格(元/公斤)'],textStyle:{{color:'#8fa8c8',fontSize:12}},top:2,itemWidth:16,itemHeight:8}},
  grid:{{left:60,right:60,top:44,bottom:34}},
  yAxis:[
    Object.assign({{type:'value',name:'万头',min:2600,max:4700,nameTextStyle:{{color:GOLD,fontSize:11}}}},AX),
    Object.assign({{type:'value',name:'元/公斤',nameTextStyle:{{color:ORANGE,fontSize:11}}}},AX)
  ],
  series:[
    {{name:'能繁母猪存栏(万头)',type:'line',yAxisIndex:0,data:SOWS,smooth:false,connectNulls:true,
      symbol:'circle',symbolSize:9,lineStyle:{{width:3,color:GOLD}},itemStyle:{{color:GOLD,borderColor:'#0a1930',borderWidth:1.5}},
      label:{{show:true,position:'top',fontSize:10,color:GOLD,formatter:p=>p.value?p.value:'',distance:7}}}},
    {{name:'猪肉价格(元/公斤)',type:'line',yAxisIndex:1,data:PORK,smooth:true,symbol:'none',
      lineStyle:{{width:2.5,color:ORANGE}},
      areaStyle:{{color:{{type:'linear',x:0,y:0,x2:0,y2:1,colorStops:[{{offset:0,color:'rgba(232,131,74,.25)'}},{{offset:1,color:'rgba(232,131,74,0)'}}]}}}}}}
  ]
}}));

// ③ 指数 vs 股价
echarts.init(document.getElementById('c3')).setOption(base({{
  legend:{{data:['中证畜牧指数','牧原股份','温氏股份'],textStyle:{{color:'#8fa8c8',fontSize:12}},top:2,itemWidth:16,itemHeight:8}},
  yAxis:Object.assign({{type:'value',name:'指数(起点=100)',nameTextStyle:{{color:'#8fa8c8',fontSize:11}}}},AX),
  series:[
    {{name:'中证畜牧指数',type:'line',data:IDX_N,smooth:true,symbol:'none',lineStyle:{{width:2.5,color:BLUE}}}},
    {{name:'牧原股份',type:'line',data:MY_N,smooth:true,symbol:'none',lineStyle:{{width:2.5,color:GREEN}}}},
    {{name:'温氏股份',type:'line',data:WS_N,smooth:true,symbol:'none',lineStyle:{{width:2.5,color:PURPLE}}}}
  ]
}}));

// ④ KPI
const fin = v => v==null ? '—' : v.toLocaleString('zh-CN');
const kv = [
  ['存栏最新（2025Q4）', fin(SOWS.filter(x=>x).slice(-1)[0])+' 万头', '2025年10月月度值'],
  ['存栏周期低点', fin(Math.min(...SOWS.filter(x=>x)))+' 万头', '2019年末（非洲猪瘟去化）'],
  ['存栏周期高点', fin(Math.max(...SOWS.filter(x=>x)))+' 万头', '2022年末'],
  ['猪价最新（2026Q3）', PORK.filter(x=>x).slice(-1)[0].toFixed(2)+' 元/kg', '季末值'],
  ['猪价周期高点', Math.max(...PORK.filter(x=>x)).toFixed(2)+' 元/kg', '2020Q2'],
  ['牧原最新', MY.filter(x=>x).slice(-1)[0].toFixed(2)+' 元', '前复权'],
  ['温氏最新', WS.filter(x=>x).slice(-1)[0].toFixed(2)+' 元', '前复权'],
  ['中证畜牧最新', fin(IDX.filter(x=>x).slice(-1)[0]), '930707']
];
document.getElementById('kpi').innerHTML = kv.map(([k,v,d])=>
  `<div class="kpi"><div class="k">${{k}}</div><div class="v">${{v}}</div><div class="d">${{d}}</div></div>`).join('');

// ⑤ 表格
let th = '<thead><tr><th>季度</th><th>能繁母猪存栏(万头)</th><th>猪肉价格(元/kg)</th><th>中证畜牧(930707)</th><th>牧原(元)</th><th>温氏(元)</th></tr></thead>';
let tb = '<tbody>' + L.map((lab,i)=>{{
  const g = GRAN[lab] ? `<span class="tag">${{GRAN[lab]}}</span>` : '';
  const f = (v,dp) => v==null ? '<span style="color:#4a6b8f">—</span>' : (dp? v.toFixed(dp) : v.toLocaleString('zh-CN'));
  return `<tr><td>${{lab}}</td><td>${{f(SOWS[i])}}${{g}}</td><td>${{f(PORK[i],2)}}</td><td>${{f(IDX[i])}}</td><td>${{f(MY[i],2)}}</td><td>${{f(WS[i],2)}}</td></tr>`;
}}).join('') + '</tbody>';
document.getElementById('tbl').innerHTML = th + tb;
</script>
</body>
</html>
"""

out = os.path.join(BASE, 'pig_cycle.html')
open(out, 'w', encoding='utf-8').write(html)
print(f'✅ 生成 {out}  ({len(html):,} 字节)')
print(f'   季度数: {len(D)}  存栏点数: {sum(1 for s in sows if s)}  猪价点数: {sum(1 for s in pork if s)}')
print(f'   归一化基准（各自首个有值季度）: 存栏={next(v for v in sows if v)}  猪价={next(v for v in pork if v)}  指数={next(v for v in idx if v)}')
