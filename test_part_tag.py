#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证持仓「部分」标记：渲染 + 点击切换 + 持久化（用桩行情，避免依赖外网接口）"""
import glob, http.server, socketserver, threading, os, functools
os.chdir('/home/administrator/invest-tools')


class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


srv = socketserver.TCPServer(('127.0.0.1', 0), functools.partial(Q, directory=os.getcwd()))
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()

from playwright.sync_api import sync_playwright
EXE = glob.glob('/home/administrator/.cache/ms-playwright/chromium-*/chrome-linux64/chrome')[0]

STUB = """() => {
  /* 桩：让行情返回固定值，使持仓表能渲染 */
  window.getStockQuote = function(secid){
    var c = String(secid).replace(/\\D/g,'').slice(-6);
    var map = {'601398': {name:'工商银行', price:6.50, preClose:6.40, vol:1e6, mainIn:1e5, code:'601398'},
               '600519': {name:'贵州茅台', price:1600,  preClose:1590, vol:2e4, mainIn:-3e4, code:'600519'},
               '000895': {name:'双汇发展', price:23.5,  preClose:23.8, vol:3e5, mainIn:2e4, code:'000895'}};
    return Promise.resolve(map[c] || {name:'测试股', price:10, preClose:10, vol:1e4, mainIn:0, code:c});
  };
  window.getHistClose = function(code, date){ return Promise.resolve(10); };
}"""

with sync_playwright() as pw:
    b = pw.chromium.launch(headless=True, executable_path=EXE, args=['--no-sandbox'])
    pg = b.new_page(viewport={'width': 1600, 'height': 1200})
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(f'http://127.0.0.1:{port}/vibe.html', wait_until='load', timeout=45000)
    pg.wait_for_timeout(2500)

    pg.evaluate("""() => {
      lsSet('holdsLog', [
        {d:todayStr(), ts:1, code:'601398', shares:10000, price:6.20, name:'工商银行', op:'set'},
        {d:todayStr(), ts:2, code:'600519', shares:100,   price:1500, name:'贵州茅台', op:'set'},
        {d:todayStr(), ts:3, code:'000895', shares:2000,  price:22.0, name:'双汇发展', op:'set'}
      ]);
      lsSet('holds', [
        {code:'601398', shares:10000, price:6.20},
        {code:'600519', shares:100,   price:1500},
        {code:'000895', shares:2000,  price:22.0}
      ]);
      lsSet('parts', {'000895':'cyc'});
    }""")
    pg.reload(wait_until='load')
    pg.wait_for_timeout(2500)
    pg.evaluate(STUB)
    pg.evaluate("switchBoardTab('hold')")
    try:
        pg.wait_for_selector('#holdList table', timeout=25000)
    except Exception as e:
        print('⚠️ 表格未渲染:', str(e)[:100])
    pg.wait_for_timeout(1200)

    r1 = pg.evaluate("""() => {
      const t = document.querySelector('#holdList table');
      if(!t) return {err:'无表'};
      const rows = [...t.querySelectorAll('tr')];
      return {
        head: [...rows[0].children].map(x=>x.innerText.trim()),
        tags: [...t.querySelectorAll('.tag-part')].map(x=>x.innerText.trim()),
        ncol: rows[0].children.length,
        totalCols: [...rows[rows.length-1].children].map(x=>x.getAttribute('colspan')||'1'),
        names: rows.slice(1,-1).map(tr=>tr.children[0].innerText.trim().split(' ')[0])
      };
    }""")
    print('表头:', r1.get('head'))
    print(f"列数: {r1.get('ncol')} | 标签: {r1.get('tags')}")
    print('合计行 colspan 分布:', r1.get('totalCols'))

    pg.evaluate("() => document.querySelector('#holdList .tag-part').click()")
    try:
        pg.wait_for_selector('#holdList table', timeout=25000)
    except Exception:
        pass
    pg.wait_for_timeout(1500)
    r2 = pg.evaluate("""() => {
      const t = document.querySelector('#holdList table');
      return {tags: t? [...t.querySelectorAll('.tag-part')].map(x=>x.innerText.trim()) : null,
              stored: JSON.stringify(lsGet('parts', {}))};
    }""")
    print('点击后标签:', r2.get('tags'), '| 存储:', r2.get('stored'))

    pg.reload(wait_until='load')
    pg.wait_for_timeout(2500)
    pg.evaluate(STUB)
    pg.evaluate("switchBoardTab('hold')")
    try:
        pg.wait_for_selector('#holdList table', timeout=25000)
    except Exception:
        pass
    pg.wait_for_timeout(1500)
    r3 = pg.evaluate("() => [...document.querySelectorAll('#holdList .tag-part')].map(x=>x.innerText.trim())")
    print('刷新后标签（持久化验证）:', r3)
    print('JS 报错:', errs[:3] if errs else '无')
    pg.screenshot(path='/home/administrator/invest-tools/parts_tag.png')
    b.close()
srv.shutdown()
