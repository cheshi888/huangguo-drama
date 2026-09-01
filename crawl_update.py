#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""黄果短剧增量更新器
- 每次运行先重新扫描全站分类页，收集当前全部剧集 ID
- 与已爬取数据对比：只爬「新增剧集」+「上次失败的重试」
- 已成功爬取的剧集完全跳过（不重复请求）
"""
import sys, json, time, os, re
sys.path.insert(0, r"E:\workspace")
import huangguo_parser as h

CATS = ["ai-duanju", "ai-manju", "ai-huanlian", "ai-mogai",
        "topics", "ranks/hot", "chigua", "go-home"]
ID_FILE = r"E:\workspace\all_ids.json"
PROG_FILE = r"E:\workspace\crawl_progress.json"
OUT_M3U = r"E:\workspace\all_playlist.m3u8"
OUT_JSON = r"E:\workspace\all_streams.json"


def pages_of(cat):
    p = h.fetch(h.SITE + "/" + cat.strip("/") + "/")
    m = re.search(r'data-pages="(\d+)"', p)
    return int(m.group(1)) if m else 1


def collect_all_ids():
    seen, order = {}, []
    for cat in CATS:
        try:
            pages = pages_of(cat)
        except Exception:
            continue
        for pg in range(1, pages + 1):
            url = h.SITE + "/" + cat.strip("/") + "/" + (("%d/" % pg) if pg > 1 else "")
            try:
                cards = h.parse_cards(h.fetch(url))
            except Exception:
                continue
            for c in cards:
                if c["id"] and c["id"] not in seen:
                    seen[c["id"]] = c["title"]
                    order.append(c["id"])
            time.sleep(0.12)
    return seen, order


def load_progress():
    if os.path.exists(PROG_FILE):
        with open(PROG_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"done": {}, "items": []}


def save_progress(prog):
    with open(PROG_FILE, "w", encoding="utf-8") as f:
        json.dump(prog, f, ensure_ascii=False)


def export(items):
    lines = ["#EXTM3U"]
    for it in items:
        if "stream" in it:
            lines.append('#EXTINF:-1 group-title="黄果短剧",%s 第%s集' % (it.get("title", ""), it.get("ep", "")))
            lines.append(it["stream"])
    with open(OUT_M3U, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump({"items": items}, f, ensure_ascii=False, indent=2)
    ok = sum(1 for i in items if "stream" in i)
    print("已导出: %s (%d 条流)" % (OUT_M3U, ok))


def crawl_one(did, title, items):
    d = h.parse_detail(h.fetch(h.SITE + "/detail/%s/" % did))
    eps = d.get("episodes") or []
    title = d.get("title") or title or did
    for e in eps:
        try:
            s = h.get_stream(e["url"], e["ep"])
            items.append({"id": did, "title": title, "ep": e["ep"],
                          "label": e["label"], "url": e["url"], "stream": s})
        except Exception as ex:
            items.append({"id": did, "title": title, "ep": e["ep"], "error": str(ex)})
        time.sleep(0.15)
    return {"title": title, "eps": len(eps)}


def main():
    print("扫描全站分类页，收集当前剧集…")
    current, order = collect_all_ids()
    print("当前全站剧集总数: %d" % len(current))

    prog = load_progress()
    done = prog.get("done", {})
    items = prog.get("items", [])

    todo_new, todo_retry = [], []
    for did in order:
        if did not in done:
            todo_new.append(did)
        elif "error" in done[did]:
            todo_retry.append(did)
    todo = todo_new + todo_retry

    print("已成功爬取: %d 部" % sum(1 for v in done.values() if "error" not in v))
    print("待爬取: 新增 %d 部, 失败重试 %d 部" % (len(todo_new), len(todo_retry)))

    if not todo:
        print("无新增内容，全部已是最新。仅刷新导出。")
        export(items)
        return

    # 移除旧失败条目（重试时避免重复追加）
    for it in items[:]:
        if "error" in it and it.get("id") in todo_retry:
            items.remove(it)

    total = len(todo)
    for i, did in enumerate(todo, 1):
        try:
            done[did] = crawl_one(did, current.get(did, ""), items)
            print("[%d/%d] %s 完成" % (i, total, did))
        except Exception as e:
            done[did] = {"error": str(e)}
            print("[%d/%d] %s 失败: %s" % (i, total, did, e))
        save_progress(prog)

    with open(ID_FILE, "w", encoding="utf-8") as f:
        json.dump({"ids": order, "titles": current}, f, ensure_ascii=False, indent=2)
    export(items)
    print("增量更新完成。")


if __name__ == "__main__":
    main()
