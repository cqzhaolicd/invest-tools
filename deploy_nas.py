#!/usr/bin/env python3
"""Deploy invest-tools index.html to Synology (SSH) + QNAP (FTP), independent dir."""
import base64, ftplib, os, sys

LOCAL = "/home/administrator/invest-tools/index.html"
PASS = "Zl150601"

# ---------- 1. Synology via SSH + base64 chunks ----------
def deploy_synology():
    import pexpect
    remote_dir = "/var/services/web/invest-tools"
    remote_file = f"{remote_dir}/index.html"
    child = pexpect.spawn("ssh -o StrictHostKeyChecking=no hermes@192.168.3.190", timeout=30, encoding="utf-8", codec_errors="replace")
    child.expect("[Pp]assword:", timeout=20)
    child.sendline(PASS)
    child.expect(r"\$", timeout=20)
    # mkdir
    child.sendline(f"mkdir -p {remote_dir}")
    child.expect(r"\$", timeout=15)
    # base64 encode
    with open(LOCAL, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("ascii")
    chunk_size = 15000
    chunks = [encoded[i:i+chunk_size] for i in range(0, len(encoded), chunk_size)]
    print(f"[Synology] {len(chunks)} chunks, {len(encoded)} b64 chars")
    mode = "wb"
    for i, c in enumerate(chunks):
        cmd = f"python3 -c \"import base64; d=base64.b64decode('{c}'); open('{remote_file}','{mode}').write(d)\""
        assert len(cmd) < 25000, f"chunk {i} too long: {len(cmd)}"
        child.sendline(cmd)
        child.expect(r"\$", timeout=60)
        mode = "ab"
        if (i+1) % 5 == 0:
            print(f"  ...{i+1}/{len(chunks)} chunks")
    # verify
    child.sendline(f"python3 -c \"c=open('{remote_file}').read(); print('OK' if '</html>' in c and len(c)=={os.path.getsize(LOCAL)} else 'TRUNCATED', len(c))\"")
    child.expect(r"\$", timeout=30)
    out = child.before
    print(f"[Synology] verify: {out.strip()[-120:]}")
    child.sendline("exit")
    child.close()

# ---------- 2. QNAP via FTP ----------
def deploy_qnap():
    ftp = ftplib.FTP()
    ftp.connect("192.168.3.88", 21, timeout=30)
    ftp.login("hermes", PASS)
    # ensure /Web/invest-tools exists
    dirs = ftp.nlst("/Web")
    if "invest-tools" not in [d.split("/")[-1] for d in dirs]:
        try:
            ftp.mkd("/Web/invest-tools")
            print("[QNAP] created /Web/invest-tools")
        except Exception as e:
            print(f"[QNAP] mkd: {e}")
    with open(LOCAL, "rb") as f:
        ftp.storbinary("STOR /Web/invest-tools/index.html", f)
    size = ftp.size("/Web/invest-tools/index.html")
    print(f"[QNAP] uploaded, remote size={size} (local={os.path.getsize(LOCAL)})")
    ftp.quit()

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "both"
    if target in ("synology", "both"):
        deploy_synology()
    if target in ("qnap", "both"):
        deploy_qnap()
    print("DONE")
