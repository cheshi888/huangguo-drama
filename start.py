#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""黄果短剧 - 通用一键启动脚本

用法:
  python start.py           启动常驻守护（播放服务 + 定时刷新 + 自动抓新剧）+ 打开浏览器
  python start.py update    手动增量更新（只爬新增，不重复）
"""
import os
import socket
import subprocess
import sys
import time
import webbrowser

BASE = os.path.dirname(os.path.abspath(__file__))
PORT = 8788

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def start_daemon():
    os.chdir(BASE)
    print("=" * 56)
    print("  黄果短剧 - 一键启动（常驻守护）")
    print("=" * 56)
    if port_in_use(PORT):
        print("[提示] 播放/订阅服务已在运行 (端口 %d)" % PORT)
    else:
        print("[启动] 启动常驻守护进程（播放服务 + 定时刷新 + 自动抓新剧）...")
        subprocess.Popen([sys.executable, "daemon.py"],
                         cwd=BASE, creationflags=CREATE_NO_WINDOW)
        time.sleep(3)
    url = "http://127.0.0.1:%d/" % PORT
    print("[打开] 浏览器 -> %s" % url)
    webbrowser.open(url)
    print()
    print("  播放面板  : %s" % url)
    print("  订阅地址  : http://%s:%d/playlist.m3u8" % (lan_ip(), PORT))
    print("  守护进程  : 后台常驻，定时刷新地址(防过期) + 自动抓新剧")
    print("  手动更新  : python start.py update")
    print()


def run_update():
    os.chdir(BASE)
    print("正在增量更新（重新扫描全站，只爬新增，不重复）...")
    print()
    subprocess.call([sys.executable, "crawl_update.py"], cwd=BASE)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("update", "-u", "--update"):
        run_update()
        input("\n更新完成，按回车键关闭...")
    else:
        start_daemon()
        input("按回车键退出（守护进程保持后台运行）...")
