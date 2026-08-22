#!/usr/bin/env python3
"""Re-upload index.html to Synology via scp (binary-safe), then verify."""
import os, pexpect, sys

LOCAL = "/home/administrator/invest-tools/index.html"
PASS = "Zl150601"
REMOTE_DIR = "/var/services/web/invest-tools"
REMOTE_FILE = f"{REMOTE_DIR}/index.html"
EXPECTED = os.path.getsize(LOCAL)

child = pexpect.spawn(
    f"scp -o StrictHostKeyChecking=no {LOCAL} hermes@192.168.3.190:{REMOTE_FILE}",
    timeout=120, encoding="utf-8", codec_errors="replace",
)
i = child.expect(["[Pp]assword:", pexpect.EOF, pexpect.TIMEOUT], timeout=30)
if i == 0:
    child.sendline(PASS)
child.expect(pexpect.EOF, timeout=120)
out = child.before or ""
print("[scp] done:", out.strip()[-200:])
child.close()

# verify via ssh
v = pexpect.spawn("ssh -o StrictHostKeyChecking=no hermes@192.168.3.190", timeout=30, encoding="utf-8", codec_errors="replace")
v.expect("[Pp]assword:", timeout=20)
v.sendline(PASS)
v.expect(r"\$", timeout=20)
v.sendline(f"python3 -c \"import os; p='{REMOTE_FILE}'; s=os.path.getsize(p); c=open(p).read(); print('SIZE', s, 'EXPECT', {EXPECTED}, 'OK' if s=={EXPECTED} and '</html>' in c else 'FAIL')\"")
v.expect(r"\$", timeout=30)
print("[verify]", (v.before or "").strip()[-150:])
v.sendline("exit")
v.close()
print("DONE")
