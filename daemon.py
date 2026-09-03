#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""黄果短剧常驻守护进程
- 后台启动播放/订阅服务 (player_server.py)
- 周期性：增量抓取新剧 + 刷新已超时的播放地址（防签名过期）

环境变量:
  REFRESH_MINUTES      刷新检查间隔（分钟，默认 30）
  REFRESH_AGE_SECONDS  地址签发超过多少秒就重新抓（默认 1800）
  PANEL_PORT           播放服务端口（默认 8788）
"""
import os
import socket
import subprocess
import sys
import time

sys.path.insert(0, r"E:\workspace")
import crawl_update as cu

BASE = r"E:\workspace"
PORT = int(os.environ.get("PANEL_PORT", "8788"))
REFRESH_MINUTES = int(os.environ.get("REFRESH_MINUTES", "30"))
REFRESH_AGE_SECONDS = int(os.environ.get("REFRESH_AGE_SECONDS", "1800"))
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def refresh_once():
    print("[%s] 开始刷新…" % time.strftime("%Y-%m-%d %H:%M:%S"))
    current, order = cu.collect_all_ids()
    prog = cu.load_progress()
    done = prog.get("done", {})
    items = prog.get("items", [])

    todo_new = [d for d in order if d not in done]
    todo_retry = [d for d in order if d in done and "error" in done[d]]
    for it in items[:]:
        if "error" in it and it.get("id") in todo_retry:
            items.remove(it)
    todo = todo_new + todo_retry

    for i, did in enumerate(todo, 1):
        try:
            done[did] = cu.crawl_one(did, current.get(did, ""), items)
            print("  [新增 %d/%d] %s" % (i, len(todo), did))
        except Exception as e:
            done[did] = {"error": str(e)}
        cu.save_progress(prog)

    ok, err, skip = cu.refresh_streams(items, max_age=REFRESH_AGE_SECONDS)
    cu.save_progress(prog)
    cu.export(items)
    print("[%s] 完成：新增 %d 部，刷新 %d 集，失败 %d 集，跳过(未过期) %d 集"
          % (time.strftime("%H:%M:%S"), len(todo), ok, err, skip))


def main():
    print("=" * 56)
    print("  黄果短剧 - 常驻守护 + 播放服务")
    print("=" * 56)
    if not port_in_use(PORT):
        print("[启动] 播放/订阅服务 (端口 %d)..." % PORT)
        subprocess.Popen([sys.executable, os.path.join(BASE, "player_server.py")],
                         cwd=BASE, creationflags=CREATE_NO_WINDOW)
        time.sleep(2)
    else:
        print("[提示] 播放服务已在运行 (端口 %d)" % PORT)
    print("[守护] 每 %d 分钟检查一次，签发超过 %d 秒的地址会重新抓取"
          % (REFRESH_MINUTES, REFRESH_AGE_SECONDS))
    print("[面板] http://127.0.0.1:%d/" % PORT)
    print("[订阅] http://<本机IP>:%d/playlist.m3u8" % PORT)
    print("常驻运行中，按 Ctrl+C 退出。")
    print()
    while True:
        try:
            refresh_once()
        except Exception as e:
            print("[%s] 刷新出错: %s" % (time.strftime("%H:%M:%S"), e))
        time.sleep(REFRESH_MINUTES * 60)


if __name__ == "__main__":
    main()
