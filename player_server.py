#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""黄果短剧播放面板 + 订阅服务
- 网页面板:  http://127.0.0.1:8788/
- 订阅地址:  http://<本机IP>:8788/playlist.m3u8   (NTPlayer/VLC 等订阅)
- 数据接口:  http://127.0.0.1:8788/api/groups
- 实时取流:  http://127.0.0.1:8788/api/stream?url=<视频页>&ep=<集数>
- 订阅代理:  http://127.0.0.1:8788/play?id=<剧集id>&ep=<集数>  (302 跳转到新鲜地址)
"""
import json
import os
import socketserver
import sys
import urllib.parse
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, r"E:\workspace")
import huangguo_parser as h

PROG = r"E:\workspace\crawl_progress.json"
ALL = r"E:\workspace\all_streams.json"
PORT = int(os.environ.get("PANEL_PORT", "8788"))


def load_items():
    src = ALL if os.path.exists(ALL) else PROG
    try:
        with open(src, encoding="utf-8") as f:
            d = json.load(f)
        return d.get("items", [])
    except Exception:
        return []


def group_items(items):
    groups = OrderedDict()
    for it in items:
        if not (it.get("url") or it.get("stream")):
            continue
        key = it.get("id", "?")
        g = groups.setdefault(key, {"id": key, "title": it.get("title", ""), "eps": []})
        g["eps"].append({
            "ep": it.get("ep"),
            "label": it.get("label"),
            "url": it.get("url"),
            "stream": it.get("stream"),
        })
    return list(groups.values())


PAGE = r'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>黄果短剧播放面板</title>
<style>
*{box-sizing:border-box}
body{margin:0;font:14px system-ui,sans-serif;background:#0f1216;color:#e6e8ea;height:100vh;display:flex;flex-direction:column}
header{padding:12px 16px;background:#171b21;border-bottom:1px solid #242a33;display:flex;align-items:center;gap:12px;flex-wrap:wrap}
header h1{margin:0;font-size:17px}
header .stat{color:#8b98a5;font-size:12px}
#kw{flex:1;min-width:200px;max-width:420px;padding:9px 12px;border-radius:8px;border:1px solid #2c343e;background:#0f1216;color:#e6e8ea;outline:none}
main{flex:1;display:flex;overflow:hidden}
#list{width:340px;min-width:260px;overflow-y:auto;border-right:1px solid #242a33;padding:8px}
.drama{border:1px solid #242a33;border-radius:8px;margin-bottom:6px;background:#171b21;overflow:hidden}
.drama-head{padding:10px 12px;cursor:pointer;display:flex;justify-content:space-between;align-items:center;gap:8px}
.drama-head:hover{background:#1d232b}
.drama-title{font-weight:600}
.drama-meta{color:#8b98a5;font-size:12px;white-space:nowrap}
.eps{display:none;padding:0 12px 10px}
.drama.open .eps{display:flex;flex-wrap:wrap;gap:6px}
.ep{padding:6px 10px;border-radius:6px;background:#242a33;cursor:pointer;font-size:13px;border:1px solid transparent}
.ep:hover{background:#2f6f64;color:#fff}
#player{flex:1;display:flex;flex-direction:column;padding:12px;gap:8px}
video{flex:1;width:100%;background:#000;border-radius:10px;max-height:calc(100vh - 120px)}
#now{color:#8b98a5;font-size:13px;min-height:20px}
.empty{color:#5b6772;text-align:center;padding:30px 10px}
@media(max-width:760px){main{flex-direction:column}#list{width:100%;border-right:0;border-bottom:1px solid #242a33}}
</style>
</head>
<body>
<header>
  <h1>黄果短剧播放面板</h1>
  <span class="stat" id="stat">加载中…</span>
  <input id="kw" placeholder="搜索剧集标题…">
</header>
<main>
  <aside id="list"><div class="empty">加载中…</div></aside>
  <section id="player">
    <video id="v" controls playsinline></video>
    <div id="now">点击左侧集数开始播放</div>
  </section>
</main>
<script src="https://cdn.jsdelivr.net/npm/hls.js@1.5.17/dist/hls.min.js"></script>
<script>
let hls=null, groups=[];
const list=document.querySelector('#list'), stat=document.querySelector('#stat'),
      now=document.querySelector('#now'), video=document.querySelector('#v'), kw=document.querySelector('#kw');
function startPlay(url, name){
  if(window.Hls&&Hls.isSupported()){
    hls=new Hls();hls.loadSource(url);hls.attachMedia(video);
    hls.on(Hls.Events.MANIFEST_PARSED,()=>video.play().catch(()=>{}));
    hls.on(Hls.Events.ERROR,(_,d)=>{if(d.fatal)now.textContent='加载失败: '+d.type+' / '+d.details});
  }else if(video.canPlayType('application/vnd.apple.mpegurl')){
    video.src=url;video.load();video.play().catch(()=>{});
  }
  now.textContent='正在播放: '+name;
}
function play(epObj, name){
  if(hls){hls.destroy();hls=null}
  video.removeAttribute('src');
  if(!epObj || !epObj.url){ now.textContent='缺少播放地址'; return; }
  now.textContent='正在获取播放地址: '+name+' …';
  fetch('/api/stream?url='+encodeURIComponent(epObj.url)+'&ep='+encodeURIComponent(epObj.ep||'1'))
    .then(r=>r.json())
    .then(d=>{ if(d.error) throw new Error(d.error); startPlay(d.stream, name); })
    .catch(e=>{ now.textContent='获取播放地址失败: '+(e.message||e); });
}
function render(data){
  groups=data;
  stat.textContent='共 '+data.length+' 部剧 / '+data.reduce((a,g)=>a+g.eps.length,0)+' 集';
  list.innerHTML='';
  data.forEach(g=>{
    const d=document.createElement('div');d.className='drama';d.dataset.title=(g.title||'').toLowerCase();
    const head=document.createElement('div');head.className='drama-head';
    head.innerHTML='<span class="drama-title"></span><span class="drama-meta">'+g.eps.length+'集</span>';
    head.querySelector('.drama-title').textContent=g.title;
    const box=document.createElement('div');box.className='eps';
    g.eps.forEach(e=>{
      const b=document.createElement('span');b.className='ep';b.textContent='第'+e.ep+'集';
      b.onclick=()=>play(e, g.title+' 第'+e.ep+'集');
      box.appendChild(b);
    });
    head.onclick=()=>d.classList.toggle('open');
    d.appendChild(head);d.appendChild(box);list.appendChild(d);
  });
}
fetch('/api/groups').then(r=>r.json()).then(render).catch(e=>{list.innerHTML='<div class="empty">加载失败: '+e.message+'</div>'});
kw.addEventListener('input',()=>{
  const q=kw.value.trim().toLowerCase();
  document.querySelectorAll('.drama').forEach(d=>{d.style.display=(!q||d.dataset.title.includes(q))?'':'none'});
});
</script>
</body>
</html>'''


def build_m3u(items, host=""):
    lines = ["#EXTM3U"]
    host = host or ("127.0.0.1:%d" % PORT)
    for it in items:
        if it.get("url"):
            lines.append('#EXTINF:-1 group-title="黄果短剧",%s 第%s集' % (it.get("title", ""), it.get("ep", "")))
            lines.append("http://%s/play?id=%s&ep=%s" % (host, it.get("id"), it.get("ep")))
        elif "stream" in it:
            lines.append('#EXTINF:-1 group-title="黄果短剧",%s 第%s集' % (it.get("title", ""), it.get("ep", "")))
            lines.append(it["stream"])
    return "\n".join(lines) + "\n"


class App(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body, ctype):
        b = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        p = urllib.parse.urlparse(self.path)
        if p.path == "/":
            self._send(200, PAGE, "text/html; charset=utf-8")
        elif p.path == "/api/groups":
            self._send(200, json.dumps(group_items(load_items()), ensure_ascii=False),
                       "application/json; charset=utf-8")
        elif p.path == "/api/stream":
            qs = urllib.parse.parse_qs(p.query)
            url = (qs.get("url") or [""])[0]
            ep = (qs.get("ep") or ["1"])[0]
            try:
                stream = h.get_stream(url, ep)
                self._send(200, json.dumps({"stream": stream}, ensure_ascii=False),
                           "application/json; charset=utf-8")
            except Exception as ex:
                self._send(500, json.dumps({"error": str(ex)}, ensure_ascii=False),
                           "application/json; charset=utf-8")
        elif p.path == "/play":
            qs = urllib.parse.parse_qs(p.query)
            did = (qs.get("id") or [""])[0]
            ep = (qs.get("ep") or ["1"])[0]
            target = next((it.get("url") for it in load_items()
                           if it.get("url") and str(it.get("id")) == did
                           and str(it.get("ep")) == ep), None)
            if not target:
                self._send(404, "not found", "text/plain; charset=utf-8")
                return
            try:
                stream = h.get_stream(target, ep)
                self.send_response(302)
                self.send_header("Location", stream)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
            except Exception as ex:
                self._send(500, "resolve failed: %s" % ex, "text/plain; charset=utf-8")
        elif p.path in ("/playlist.m3u8", "/subscribe", "/playlist.m3u"):
            host = self.headers.get("Host") or ""
            self._send(200, build_m3u(load_items(), host),
                       "application/vnd.apple.mpegurl; charset=utf-8")
        else:
            self._send(404, "not found", "text/plain; charset=utf-8")


if __name__ == "__main__":
    print("播放面板: http://127.0.0.1:%d/" % PORT)
    print("订阅地址: http://<本机IP>:%d/playlist.m3u8" % PORT)
    with socketserver.ThreadingTCPServer(("0.0.0.0", PORT), App) as srv:
        srv.serve_forever()

