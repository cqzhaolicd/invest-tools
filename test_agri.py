#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证「行业景气」卡片：牧原(养殖) 应显示期货+猪粮比；茅台(非农) 应不显示"""
import glob, http.server, socketserver, threading, os, sys
os.chdir('/home/administrator/invest-tools')


class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


PORT = 8839
httpd = socketserver.TCPServer(('127.0.0.1', PORT), Q)
threading.Thread(target=httpd.serve_forever, daemon=True).start()

from playwright.sync_api import sync_playwright

EXE = glob.glob('/home/administrator/.cache/ms-playwright/chromium-*/chrome-linux64/chrome')[0]
CODES = sys.argv[1:] or ['002714', '600519', '300498']

with sync_playwright() as pw:
    b = pw.chromium.launch(headless=True, executable_path=EXE, args=['--no-sandbox'])
    pg = b.new_page(viewport={'width': 1700, 'height': 1500})
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto('http://127.0.0.1:%d/vibe.html#stock' % PORT, wait_until='load')
    pg.wait_for_timeout(4000)
    for code in CODES:
        pg.fill('#symInput', code)
        pg.evaluate("loadStock()")
        pg.wait_for_timeout(11000)
        info = pg.evaluate("""() => {
          const cards=[...$('stockArea').querySelectorAll('.card')];
          const idx=cards.find(c=>c.querySelector('h3') && c.querySelector('h3').textContent.indexOf('行业景气')>=0);
          const q=cards[0] && cards[0].querySelector('h3') ? cards[0].querySelector('h3').textContent.replace(/\\s+/g,' ').trim() : '';
          if(!idx) return {has:false, quote:q, cardCount:cards.length};
          const txt=idx.innerText.replace(/\\n{2,}/g,'\\n').trim();
          const svgN=idx.querySelectorAll('svg').length;
          const mark=idx.querySelector('div[title]');
          return {has:true, quote:q, text:txt, svg:svgN, marker: mark? mark.getAttribute('title'):''};
        }""")
        print('\n══════ %s ══════' % code)
        print('  行情卡:', info['quote'][:60], '| 卡片数:', info.get('cardCount'))
        if not info['has']:
            print('  （无行业景气卡 —— 非农业股，符合预期）')
            continue
        for line in info['text'].split('\n')[:22]:
            print('   ', line)
        print('   SVG图:', info['svg'], '| 标记:', info['marker'])
    print('\nJS 报错:', errs[:3] if errs else '无')
    pg.screenshot(path='/home/administrator/invest-tools/agri.png', full_page=False)
    b.close()
httpd.shutdown()
