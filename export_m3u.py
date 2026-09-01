import json, os
from collections import OrderedDict

PROG = r"E:\workspace\crawl_progress.json"
ALL = r"E:\workspace\all_streams.json"
OUT_M3U = r"E:\workspace\progress_playlist.m3u8"


def load_items():
    src = ALL if os.path.exists(ALL) else PROG
    d = json.load(open(src, encoding="utf-8"))
    return d.get("items", [])


def main():
    items = load_items()
    groups = OrderedDict()
    for it in items:
        if "stream" not in it:
            continue
        groups.setdefault(it.get("id", "?"), []).append(it)

    lines = ["#EXTM3U", "#EXT-X-VERSION:3"]
    for key, its in groups.items():
        for it in its:
            lines.append("#EXTINF:-1,%s 第%s集" % (it.get("title", ""), it.get("ep", "")))
            lines.append(it["stream"])
    with open(OUT_M3U, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    ok = sum(1 for it in items if "stream" in it)
    print("播放列表已生成:", OUT_M3U)
    print("共 %d 条流 / %d 部剧" % (ok, len(groups)))
    print("\n已解析剧集列表:")
    for i, (key, its) in enumerate(groups.items()):
        print("  %-6s %-28s %d集" % (key, its[0].get("title", "")[:28], len(its)))


if __name__ == "__main__":
    main()
