#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""黄果短剧 - 通用一键启动脚本

用法:
  python start.py           启动播放面板 + 打开浏览器
  python start.py update    增量更新（只爬新增，不重复）
"""
import os
import socket
import subprocess
import sys
import time
import webbrowser

BASE = r"E:\workspace"
PORT = 8788

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def start_panel():
    os.chdir(BASE)
    print("=" * 54)
    print("  黄果短剧 - 播放面板一键启动")
    print("=" * 54)
    if port_in_use(PORT):
        print("[提示] 播放面板服务已在运行 (端口 %d)" % PORT)
    else:
        print("[启动] 正在后台启动播放面板服务...")
        subprocess.Popen([sys.executable, "player_server.py"],
                         cwd=BASE, creationflags=CREATE_NO_WINDOW)
        time.sleep(2)
    url = "http://127.0.0.1:%d/" % PORT
    print("[打开] 浏览器 -> %s" % url)
    webbrowser.open(url)
    print()
    print("  播放面板  : %s" % url)
    print("  订阅地址1 : http://192.168.1.45:%d/playlist.m3u8" % PORT)
    print("  订阅地址2 : http://192.168.125.5:%d/playlist.m3u8" % PORT)
    print("  增量更新  : python start.py update")
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
        start_panel()
        input("按回车键退出（服务保持后台运行）...")
