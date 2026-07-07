"""One-shot VPS deployment script. Set VPS_PASS env var before running."""
import os
import sys
import time

import paramiko

HOST = os.environ.get("VPS_HOST", "198.177.123.152")
USER = os.environ.get("VPS_USER", "root")
PASS = os.environ.get("VPS_PASS", "")

INSTALL_SCRIPT = r"""
set -e
rm -rf /tmp/map-scraper-install
git clone --depth 1 https://github.com/smarthashmi/Google-Map-Scrapper-Web-Based-with-Python.git /tmp/map-scraper-install
chmod +x /tmp/map-scraper-install/deploy/install.sh
bash /tmp/map-scraper-install/deploy/install.sh
"""


def run(ssh, cmd, timeout=900):
    print(f"\n>>> running remote command ({len(cmd)} chars)...")
    _, stdout, _ = ssh.exec_command(cmd, timeout=timeout, get_pty=True)
    while True:
        if stdout.channel.recv_ready():
            print(stdout.channel.recv(4096).decode("utf-8", errors="replace"), end="", flush=True)
        if stdout.channel.exit_status_ready():
            while stdout.channel.recv_ready():
                print(stdout.channel.recv(4096).decode("utf-8", errors="replace"), end="", flush=True)
            break
        time.sleep(0.2)
    return stdout.channel.recv_exit_status()


def main():
    if not PASS:
        print("Set VPS_PASS environment variable before running.")
        sys.exit(1)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, port=22, username=USER, password=PASS, timeout=30)

    run(ssh, "free -h; df -h /; ss -tlnp | head -20")
    code = run(ssh, INSTALL_SCRIPT, timeout=900)
    if code != 0:
        run(ssh, "journalctl -u map-scraper -n 50 --no-pager")
        ssh.close()
        sys.exit(code)

    run(ssh, "curl -s -o /dev/null -w 'getclover :80 -> %{http_code}\n' http://127.0.0.1:80/")
    run(ssh, "curl -s -o /dev/null -w 'scraper :8080 -> %{http_code}\n' http://127.0.0.1:8080/")
    run(ssh, "systemctl is-active getclover map-scraper nginx")
    run(ssh, "free -h")
    ssh.close()
    print("\nDeployment finished successfully.")


if __name__ == "__main__":
    main()
