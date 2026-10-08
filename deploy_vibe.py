#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""部署投资中心到三地：群晖(scp -O) + 威联通(FTP) + GitHub(gh-pages)

注意：群晖 SFTP 子系统被 chroot，scp 必须加 -O（传统协议），否则报 No such file or directory。
"""
import ftplib, hashlib, os, re, shlex, subprocess, sys
import pexpect

REPO = '/home/administrator/invest-tools'
PASS = open(__import__('os').path.expanduser('~/.ssh/.qnap_pw')).read().strip()
SYNO_DIR = '/var/services/web/invest-tools'
QNAP_DIR = '/Web/invest-tools'
QNAP_SKIP = os.path.expanduser('~/.hermes/state/qnap_skip_until')   # 免打扰开关（过期自动失效）

# 需要部署的文件（相对仓库路径）
FILES = ['vibe.html', 'data/sequoia.json', 'data/agri.json', 'data/duanT.json', 'data/tradecal.json',
         'pig_cycle.html', 'data/pig_cycle/quarterly.json', 'data/pig_cycle/daily.json',
         'lib/echarts.min.js']
# 需要预建的子目录（scp/FTP 不会自动建父目录）
SUBDIRS = ['data', 'data/pig_cycle', 'lib']
COMMIT_MSG = os.environ.get('DEPLOY_MSG', '更新投资中心页面')


def qnap_skipped():
    """威联通免打扰：开关文件内容为日期，当天 <= 该日期则跳过"""
    try:
        import datetime
        d = datetime.date.fromisoformat(open(QNAP_SKIP).read().strip())
        return datetime.date.today() <= d, d
    except Exception:
        return False, None

md5 = lambda p: hashlib.md5(open(p, 'rb').read()).hexdigest()


SYNO_KEY = os.path.expanduser('~/.ssh/id_ed25519_syno')
SYNO_USER = 'cqzhaoli'          # 已配公钥免密（StrictModes 已修，家目录 700）
SYNO_HOST = '192.168.3.190'


def _ssh(args, timeout=120):
    r = subprocess.run(['ssh', '-i', SYNO_KEY, '-o', 'StrictHostKeyChecking=no',
                        '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15',
                        f'{SYNO_USER}@{SYNO_HOST}'] + args,
                       capture_output=True, text=True, timeout=timeout)
    return r.returncode, (r.stdout + r.stderr)


def synology():
    ok = True
    rc, out = _ssh(['mkdir -p ' + ' '.join(f'{SYNO_DIR}/{d}' for d in SUBDIRS)])
    if rc != 0:
        print(f'[群晖] ❌ 建目录失败: {out[:160]}')
        return f'❌ 建目录失败: {out[:120]}'
    for rel in FILES:
        local = os.path.join(REPO, rel)
        remote = f'{SYNO_DIR}/{rel}'
        r = subprocess.run(['scp', '-O', '-i', SYNO_KEY, '-o', 'StrictHostKeyChecking=no',
                            '-o', 'BatchMode=yes', local, f'{SYNO_USER}@{SYNO_HOST}:{remote}'],
                           capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            print(f'[群晖] {rel}: ❌ {(r.stdout + r.stderr)[:140]}')
            ok = False
            continue
        rc, out = _ssh([f'md5sum {remote}'])
        m = re.search(r'([0-9a-f]{32})\s+', out)
        remote_md5 = m.group(1) if m else '(未取到)'
        good = remote_md5 == md5(local)
        ok = ok and good
        print(f'[群晖] {rel}: {"✅" if good else "❌"} 本地{md5(local)[:8]} 远端{str(remote_md5)[:8]}')
    return ok


def qnap():
    skip, until = qnap_skipped()
    if skip:
        print(f'[威联通] 🔇 免打扰中（开关至 {until}），本次跳过')
        return '🔇 已跳过（免打扰）'
    ok = True
    ftp = ftplib.FTP()
    ftp.connect('192.168.3.88', 21, timeout=90)
    ftp.login('hermes', PASS)
    for _sub in SUBDIRS:
        try:
            ftp.mkd(f'{QNAP_DIR}/{_sub}')
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
        rc, out = run('git -c user.name=hermes -c user.email=hermes@local commit -m ' + shlex.quote(COMMIT_MSG))
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
