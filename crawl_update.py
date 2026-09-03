#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""黄果短剧增量更新器（并行高性能版）
- 并行扫描全站分类页，收集当前全部剧集 ID
- 与已爬取数据对比：只爬「新增剧集」+「上次失败的重试」
- 并行取流（多集/多剧并发），低内存低延迟
"""
import sys, json, time, os, re
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, r"E:\workspace")
import huangguo_parser as h

CATS = ["ai-duanju", "ai-manju", "ai-huanlian", "ai-mogai",
        "topics", "ranks/hot", "chigua", "go-home"]
ID_FILE = r"E:\workspace\all_ids.json"
PROG_FILE = r"E:\workspace\crawl_progress.json"
OUT_M3U = r"E:\workspace\all_playlist.m3u8"
OUT_JSON = r"E:\workspace\all_streams.json"

# 并发线程数（线程池，内存开销小）。可通过环境变量 CRAWL_WORKERS 调整。
# 网站对并发有惩罚，过高反而触发限流，12 是较稳健的值。
WORKERS = int(os.environ.get("CRAWL_WORKERS", "12"))


def parallel_map(fn, args, workers=None):
    """线程池并行 map，保持参数顺序。args 为空时直接返回空列表。"""
    args = list(args)
    if not args:
        return []
    w = workers or WORKERS
    w = max(1, min(w, len(args)))
    with ThreadPoolExecutor(max_workers=w) as ex:
        return list(ex.map(fn, args))


def pages_of(cat):
    p = h.fetch(h.SITE + "/" + cat.strip("/") + "/")
    m = re.search(r'data-pages="(\d+)"', p)
    return int(m.group(1)) if m else 1


def collect_all_ids(limit=None):
    """扫描全站分类页收集剧集 ID。
    limit：每个分类最多扫多少页（None=全部；用于快速检查时传 1~3）。"""
    # 1) 并行获取各分类页数
    def cat_pages(cat):
        try:
            return cat, pages_of(cat)
        except Exception:
            return cat, 0
    pages_by_cat = dict(parallel_map(cat_pages, CATS, workers=len(CATS)))

    # 2) 生成全站所有分类页 URL
    page_urls = []
    for cat in CATS:
        total = pages_by_cat.get(cat, 0)
        if limit is not None:
            total = min(total, limit)
        for pg in range(1, total + 1):
            page_urls.append(h.SITE + "/" + cat.strip("/") + "/"
                             + (("%d/" % pg) if pg > 1 else ""))

    # 3) 并行抓取所有分类页并解析卡片
    def fetch_cards(url):
        try:
            return h.parse_cards(h.fetch(url))
        except Exception:
            return []

    seen, order = {}, []
    for cards in parallel_map(fetch_cards, page_urls):
        for c in cards:
            if c["id"] and c["id"] not in seen:
                seen[c["id"]] = c["title"]
                order.append(c["id"])
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

    def fetch_ep(e):
        try:
            s = h.get_stream(e["url"], e["ep"])
            return {"id": did, "title": title, "ep": e["ep"],
                    "label": e["label"], "url": e["url"], "stream": s}
        except Exception as ex:
            return {"id": did, "title": title, "ep": e["ep"], "error": str(ex)}

    items.extend(parallel_map(fetch_ep, eps, workers=min(len(eps), 20)))
    return {"title": title, "eps": len(eps)}


def stream_age(stream):
    """返回 stream 的 auth_key 签发时间距今的秒数；无法解析时返回 None"""
    m = re.search(r"auth_key=(\d+)-", stream or "")
    if not m:
        return None
    return int(time.time()) - int(m.group(1))


def refresh_streams(items, max_age=1800):
    """并行重新抓取已超时的剧集播放地址（防签名过期）。max_age：签发超过多少秒才刷新"""
    todo = []
    for it in items:
        if not it.get("url"):
            continue
        age = stream_age(it.get("stream"))
        if age is not None and age < max_age:
            continue
        todo.append(it)

    def do(it):
        try:
            it["stream"] = h.get_stream(it["url"], it["ep"])
            it.pop("error", None)
            return "ok"
        except Exception as ex:
            it["error"] = str(ex)
            return "err"

    results = parallel_map(do, todo)
    return results.count("ok"), results.count("err"), len(items) - len(todo)


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
