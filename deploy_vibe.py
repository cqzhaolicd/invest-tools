#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""部署 vibe.html 到三地：群晖(SSH/scp) + 威联通(FTP) + GitHub(gh-pages)"""
import ftplib, hashlib, os, subprocess, sys
import pexpect

LOCAL = '/home/administrator/invest-tools/vibe.html'
PASS = 'Zl150601'
SIZE = os.path.getsize(LOCAL)
MD5 = hashlib.md5(open(LOCAL, 'rb').read()).hexdigest()
print(f'本地 vibe.html: {SIZE} 字节  md5={MD5}')

# ---------- 1. 群晖 ----------
def synology():
    remote = '/var/services/web/invest-tools/vibe.html'
    c = pexpect.spawn(f'scp -O -o StrictHostKeyChecking=no {LOCAL} hermes@192.168.3.190:{remote}',
                      timeout=180, encoding='utf-8', codec_errors='replace')
    i = c.expect(['[Pp]assword:', pexpect.EOF, pexpect.TIMEOUT], timeout=30)
    if i == 0:
        c.sendline(PASS)
    c.expect(pexpect.EOF, timeout=180)
    c.close()
    v = pexpect.spawn('ssh -o StrictHostKeyChecking=no hermes@192.168.3.190',
                      timeout=60, encoding='utf-8', codec_errors='replace')
    v.expect('[Pp]assword:', timeout=20); v.sendline(PASS); v.expect(r'[\$#]', timeout=20)
    v.sendline(f'md5sum {remote}; stat -c%s {remote}')
    v.expect(r'[\$#]', timeout=30)
    out = v.before.strip()
    v.sendline('exit'); v.close()
    print(f'[群晖] {out}')
    return MD5 in out

# ---------- 2. 威联通 ----------
def qnap():
    ftp = ftplib.FTP()
    ftp.connect('192.168.3.88', 21, timeout=60)
    ftp.login('hermes', PASS)
    with open(LOCAL, 'rb') as f:
        ftp.storbinary('STOR /Web/invest-tools/vibe.html', f)
    size = ftp.size('/Web/invest-tools/vibe.html')
    ftp.quit()
    print(f'[威联通] 远端字节={size} (本地={SIZE})')
    return size == SIZE

# ---------- 3. GitHub ----------
def github():
    repo = '/home/administrator/invest-tools'
    def run(cmd, **kw):
        r = subprocess.run(cmd, shell=True, cwd=repo, capture_output=True, text=True, **kw)
        return r.returncode, (r.stdout + r.stderr).strip()
    for f in ['test_dims.js', 'test_render.py', 'watch_judge.png']:
        run(f'git rm --cached {f} 2>/dev/null; echo {f} >> .git/info/exclude')
    run('git add vibe.html')
    rc, out = run('git status --short')
    print('[GitHub] 待提交:', out or '(无变化)')
    if out.strip():
        rc, out = run('git -c user.name=hermes -c user.email=hermes@local commit -m '
                      '"自选股新增「位置判断/动作」列: 内置《股票维度参考》七维度引擎'
                      '(市场/MACD零轴/信号/量能/次数/拥挤度 + Sequoia板块周期)"')
        print('[GitHub] commit:', out[:200])
    rc, out = run('git push origin gh-pages 2>&1')
    print('[GitHub] push rc=%d: %s' % (rc, out[:300]))
    return rc == 0

if __name__ == '__main__':
    t = sys.argv[1] if len(sys.argv) > 1 else 'both'
    ok = {}
    if t in ('synology', 'both'):
        try: ok['群晖'] = synology()
        except Exception as e: ok['群晖'] = f'❌ {e}'
    if t in ('qnap', 'both'):
        try: ok['威联通'] = qnap()
        except Exception as e: ok['威联通'] = f'❌ {e}'
    if t in ('github', 'both'):
        try: ok['GitHub'] = github()
        except Exception as e: ok['GitHub'] = f'❌ {e}'
    print('\n=== 部署结果 ===')
    for k, v in ok.items():
        print(f'  {k}: {v}')
