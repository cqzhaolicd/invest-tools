#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""部署投资中心到三地：群晖(scp -O) + 威联通(FTP) + GitHub(gh-pages)

注意：群晖 SFTP 子系统被 chroot，scp 必须加 -O（传统协议），否则报 No such file or directory。
"""
import ftplib, hashlib, os, re, subprocess, sys
import pexpect

REPO = '/home/administrator/invest-tools'
PASS = 'Zl150601'
SYNO_DIR = '/var/services/web/invest-tools'
QNAP_DIR = '/Web/invest-tools'

# 需要部署的文件（相对仓库路径）
FILES = ['vibe.html', 'data/sequoia.json', 'data/agri.json', 'data/duanT.json', 'data/tradecal.json']

md5 = lambda p: hashlib.md5(open(p, 'rb').read()).hexdigest()


def synology():
    ok = True
    c = pexpect.spawn('ssh -o StrictHostKeyChecking=no hermes@192.168.3.190',
                      timeout=60, encoding='utf-8', codec_errors='replace')
    c.expect('[Pp]assword:', timeout=20); c.sendline(PASS); c.expect(r'[\$#]', timeout=20)
    c.sendline(f'mkdir -p {SYNO_DIR}/data')
    c.expect(r'[\$#]', timeout=20)
    for rel in FILES:
        local = os.path.join(REPO, rel)
        remote = f'{SYNO_DIR}/{rel}'
        s = pexpect.spawn(f'scp -O -o StrictHostKeyChecking=no {local} hermes@192.168.3.190:{remote}',
                          timeout=180, encoding='utf-8', codec_errors='replace')
        i = s.expect(['[Pp]assword:', pexpect.EOF, pexpect.TIMEOUT], timeout=40)
        if i == 0:
            s.sendline(PASS)
        s.expect(pexpect.EOF, timeout=180)
        s.close()
        c.sendline(f'md5sum {remote}')
        c.expect(r'[\$#]', timeout=40)
        out = c.before or ''
        m = re.search(r'([0-9a-f]{32})\s+' + re.escape(remote), out)
        remote_md5 = m.group(1) if m else '(未取到)'
        good = remote_md5 == md5(local)
        ok = ok and good
        print(f'[群晖] {rel}: {"✅" if good else "❌"} 本地{md5(local)[:8]} 远端{str(remote_md5)[:8]}')
    c.sendline('exit'); c.close()
    return ok


def qnap():
    ok = True
    ftp = ftplib.FTP()
    ftp.connect('192.168.3.88', 21, timeout=90)
    ftp.login('hermes', PASS)
    try:
        ftp.mkd(f'{QNAP_DIR}/data')
    except Exception:
        pass
    for rel in FILES:
        local = os.path.join(REPO, rel)
        with open(local, 'rb') as f:
            ftp.storbinary(f'STOR {QNAP_DIR}/{rel}', f)
        size = ftp.size(f'{QNAP_DIR}/{rel}')
        good = size == os.path.getsize(local)
        ok = ok and good
        print(f'[威联通] {rel}: {"✅" if good else "❌"} 本地{os.path.getsize(local)} 远端{size}')
    ftp.quit()
    return ok


def github():
    def run(cmd):
        r = subprocess.run(cmd, shell=True, cwd=REPO, capture_output=True, text=True)
        return r.returncode, (r.stdout + r.stderr).strip()
    run('git add ' + ' '.join(FILES))
    rc, st = run('git status --short')
    print('[GitHub] 待提交:', st or '(无变化)')
    if st.strip():
        rc, out = run('git -c user.name=hermes -c user.email=hermes@local commit -m '
                      '"Sequoia-X 新增「维度位置选股」板块：全市场套用股票维度参考七维度，'
                      '挑出磨底/左侧试仓/右侧确认/主升启动各10只"')
        print('[GitHub] commit:', out[:160])
    rc, out = run('git push origin gh-pages 2>&1')
    print(f'[GitHub] push rc={rc}: {out[:220]}')
    return rc == 0


if __name__ == '__main__':
    t = sys.argv[1] if len(sys.argv) > 1 else 'both'
    res = {}
    if t in ('synology', 'both'):
        try: res['群晖'] = synology()
        except Exception as e: res['群晖'] = f'❌ {e}'
    if t in ('qnap', 'both'):
        try: res['威联通'] = qnap()
        except Exception as e: res['威联通'] = f'❌ {e}'
    if t in ('github', 'both'):
        try: res['GitHub'] = github()
        except Exception as e: res['GitHub'] = f'❌ {e}'
    print('\n=== 部署结果 ===')
    for k, v in res.items():
        print(f'  {k}: {v}')
