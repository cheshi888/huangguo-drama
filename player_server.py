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

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import huangguo_parser as h

PROG = os.path.join(BASE, "crawl_progress.json")
ALL = os.path.join(BASE, "all_streams.json")
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
:root{
  --bg:#0a0d14;--panel:#121827;--panel2:#1a2134;--line:#232c42;
  --text:#e9edf5;--muted:#8b96ad;--accent:#ff6a3d;--accent2:#ff8a5c;
  --r:14px;--shadow:0 10px 40px rgba(0,0,0,.5);
}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{height:100%}
body{margin:0;font:14px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,"PingFang SC","Microsoft YaHei",sans-serif;
  background:radial-gradient(1100px 520px at 15% -8%,#182340 0%,var(--bg) 55%) fixed;color:var(--text);min-height:100vh}
::-webkit-scrollbar{width:8px;height:8px}
::-webkit-scrollbar-thumb{background:#2a3348;border-radius:8px}
a{color:inherit;text-decoration:none}
button{font-family:inherit;cursor:pointer}

/* 顶栏 */
.topbar{position:sticky;top:0;z-index:20;display:flex;align-items:center;gap:14px;
  padding:12px 18px;background:rgba(10,13,20,.82);backdrop-filter:blur(12px);
  border-bottom:1px solid var(--line)}
.logo{font-size:18px;font-weight:800;white-space:nowrap;letter-spacing:.5px}
.logo .dot{color:var(--accent)}
#kw{flex:1;min-width:120px;max-width:460px;padding:10px 14px;border-radius:10px;
  border:1px solid var(--line);background:var(--panel);color:var(--text);outline:none;font-size:14px}
#kw:focus{border-color:var(--accent)}
.stat{color:var(--muted);font-size:12px;white-space:nowrap}

/* 主体 */
main{max-width:1400px;margin:0 auto;padding:18px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:14px}
.drama{background:var(--panel);border:1px solid var(--line);border-radius:var(--r);overflow:hidden;
  transition:transform .15s,box-shadow .15s,border-color .15s;display:flex;flex-direction:column}
.drama:hover{transform:translateY(-3px);border-color:#34405f;box-shadow:var(--shadow)}
.drama-head{padding:13px 14px;cursor:pointer;display:flex;justify-content:space-between;align-items:center;gap:8px}
.drama-title{font-weight:700;font-size:15px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.drama-meta{color:var(--muted);font-size:12px;white-space:nowrap}
.eps{display:none;padding:0 12px 12px;flex-wrap:wrap;gap:7px}
.drama.open .eps{display:flex}
.drama.open{border-color:var(--accent)}
.ep{padding:7px 11px;border-radius:9px;background:var(--panel2);cursor:pointer;font-size:13px;
  border:1px solid transparent;transition:.12s;color:var(--text)}
.ep:hover{background:var(--accent);color:#fff;border-color:var(--accent)}
.ep.active{background:var(--accent);color:#fff}
.empty{color:var(--muted);text-align:center;padding:60px 10px}

/* 播放器浮层 */
.overlay{position:fixed;inset:0;z-index:50;background:rgba(4,6,10,.88);backdrop-filter:blur(6px);
  display:flex;align-items:center;justify-content:center;padding:14px;animation:fade .18s}
.overlay.hidden{display:none}
@keyframes fade{from{opacity:0}to{opacity:1}}
.player{width:100%;max-width:1100px;max-height:100%;background:var(--panel);border:1px solid var(--line);
  border-radius:var(--r);overflow:hidden;display:flex;flex-direction:column;box-shadow:var(--shadow)}
.phead{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:12px 14px;border-bottom:1px solid var(--line)}
.ptitle{font-weight:700;font-size:15px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.pbtns{display:flex;gap:8px;flex-shrink:0}
.pbtn{width:38px;height:38px;border-radius:10px;border:1px solid var(--line);background:var(--panel2);
  color:var(--text);font-size:16px;display:flex;align-items:center;justify-content:center;transition:.12s}
.pbtn:hover{border-color:var(--accent);color:#fff}
.pbtn.close:hover{background:#e5484d;border-color:#e5484d}
video{width:100%;background:#000;aspect-ratio:16/9;max-height:62vh;display:block}
.peps{display:flex;gap:7px;overflow-x:auto;padding:12px 14px;border-top:1px solid var(--line);flex-wrap:nowrap}
.peps .ep{flex-shrink:0}

/* 响应式 */
@media(max-width:760px){
  .topbar{padding:10px 12px;gap:10px}
  .logo{font-size:16px}
  .stat{display:none}
  main{padding:12px}
  .grid{grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px}
  .drama-head{padding:11px 12px}
  .drama-title{font-size:14px}
  .overlay{padding:0}
  .player{border-radius:0;max-height:100vh;height:100%}
  video{max-height:none;flex:1}
  .pbtn{width:40px;height:40px}
}
</style>
</head>
<body>
<header class="topbar">
  <div class="logo">🍿 黄果短剧<span class="dot">·</span>播放器</div>
  <input id="kw" placeholder="搜索剧集标题…">
  <span class="stat" id="stat">加载中…</span>
</header>
<main>
  <div id="grid" class="grid"></div>
  <div id="empty" class="empty">加载中…</div>
</main>

<div id="overlay" class="overlay hidden">
  <div class="player">
    <div class="phead">
      <div class="ptitle" id="ptitle"></div>
      <div class="pbtns">
        <button class="pbtn" id="bprev" title="上一集">⏮</button>
        <button class="pbtn" id="bnext" title="下一集">⏭</button>
        <button class="pbtn" id="bfull" title="全屏 / 退出全屏">⛶</button>
        <button class="pbtn close" id="bclose" title="关闭">✕</button>
      </div>
    </div>
    <video id="v" controls playsinline webkit-playsinline></video>
    <div class="peps" id="peps"></div>
  </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/hls.js@1.5.17/dist/hls.min.js" onerror="var s=document.createElement('script');s.src='https://unpkg.com/hls.js@1.5.17/dist/hls.min.js';document.head.appendChild(s)"></script>
<script>
let hls=null, groups=[], cur={g:-1,i:-1};
const $=id=>document.getElementById(id);
const grid=$('grid'), empty=$('empty'), stat=$('stat'), kw=$('kw');
const overlay=$('overlay'), video=$('v'), ptitle=$('ptitle'), peps=$('peps');

function startPlay(url){
  if(hls){hls.destroy();hls=null}
  video.removeAttribute('src');
  if(window.Hls && Hls.isSupported()){
    hls=new Hls();
    hls.loadSource(url);
    hls.attachMedia(video);
    hls.on(Hls.Events.MANIFEST_PARSED,()=>video.play().catch(()=>{}));
    hls.on(Hls.Events.ERROR,(_,d)=>{if(d.fatal)ptitle.textContent='加载失败: '+d.type+' / '+d.details});
  }else if(video.canPlayType('application/vnd.apple.mpegurl')){
    video.src=url;video.load();video.play().catch(()=>{});
  }
}
function playEp(gi,ei){
  const g=groups[gi];if(!g)return;
  const e=g.eps[ei];if(!e)return;
  cur={g:gi,i:ei};
  overlay.classList.remove('hidden');
  renderPeps();
  if(!e.url){ptitle.textContent=g.title+' · 第'+e.ep+'集 (无地址)';return;}
  ptitle.textContent=g.title+' · 第'+e.ep+'集 (获取中…)';
  fetch('/api/stream?url='+encodeURIComponent(e.url)+'&ep='+encodeURIComponent(e.ep||'1'))
    .then(r=>r.json())
    .then(d=>{if(d.error)throw new Error(d.error);startPlay(d.stream);ptitle.textContent=g.title+' · 第'+e.ep+'集';})
    .catch(err=>{ptitle.textContent='获取失败: '+(err.message||err);});
}
function renderPeps(){
  const g=groups[cur.g];if(!g){peps.innerHTML='';return;}
  peps.innerHTML='';
  g.eps.forEach((e,ei)=>{
    const b=document.createElement('span');
    b.className='ep'+(ei===cur.i?' active':'');
    b.textContent='第'+e.ep+'集';
    b.onclick=()=>playEp(cur.g,ei);
    peps.appendChild(b);
  });
  const act=peps.querySelector('.ep.active');
  if(act)act.scrollIntoView({inline:'center',block:'nearest'});
}
function prev(){if(cur.i>0)playEp(cur.g,cur.i-1);}
function next(){const g=groups[cur.g];if(g&&cur.i<g.eps.length-1)playEp(cur.g,cur.i+1);}
function closePlayer(){
  if(hls){hls.destroy();hls=null;}
  video.pause();video.removeAttribute('src');video.load();
  overlay.classList.add('hidden');cur={g:-1,i:-1};
}
function toggleFull(){
  if(document.fullscreenElement){document.exitFullscreen().catch(()=>{});}
  else{const el=overlay.requestFullscreen?overlay:video;el.requestFullscreen().catch(()=>{});}
}
function render(data){
  groups=data;
  const eps=groups.reduce((a,g)=>a+g.eps.length,0);
  stat.textContent='共 '+groups.length+' 部 / '+eps+' 集';
  grid.innerHTML='';
  groups.forEach((g,gi)=>{
    const d=document.createElement('div');d.className='drama';d.dataset.title=(g.title||'').toLowerCase();
    const head=document.createElement('div');head.className='drama-head';
    head.innerHTML='<span class="drama-title"></span><span class="drama-meta">'+g.eps.length+'集</span>';
    head.querySelector('.drama-title').textContent=g.title;
    const box=document.createElement('div');box.className='eps';
    g.eps.forEach((e,ei)=>{
      const b=document.createElement('span');b.className='ep';b.textContent='第'+e.ep+'集';
      b.onclick=()=>playEp(gi,ei);
      box.appendChild(b);
    });
    head.onclick=()=>d.classList.toggle('open');
    d.appendChild(head);d.appendChild(box);grid.appendChild(d);
  });
  empty.style.display=groups.length?'none':'block';
}
$('bprev').onclick=prev;
$('bnext').onclick=next;
$('bfull').onclick=toggleFull;
$('bclose').onclick=closePlayer;
overlay.addEventListener('click',e=>{if(e.target===overlay)closePlayer();});
document.addEventListener('keydown',e=>{
  if(overlay.classList.contains('hidden'))return;
  if(e.key==='Escape')closePlayer();
  else if(e.key==='ArrowLeft')prev();
  else if(e.key==='ArrowRight')next();
});
kw.addEventListener('input',()=>{
  const q=kw.value.trim().toLowerCase();
  document.querySelectorAll('.drama').forEach(d=>{d.style.display=(!q||d.dataset.title.includes(q))?'':'none'});
});
fetch('/api/groups').then(r=>r.json()).then(render).catch(e=>{empty.textContent='加载失败: '+e.message;empty.style.display='block';});
</script>
</body>
</html>'''


def build_m3u(items):
    lines = ["#EXTM3U"]
    for it in items:
        if "stream" in it:
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
            self._send(200, build_m3u(load_items()),
                       "application/vnd.apple.mpegurl; charset=utf-8")
        else:
            self._send(404, "not found", "text/plain; charset=utf-8")


if __name__ == "__main__":
    print("播放面板: http://127.0.0.1:%d/" % PORT)
    print("订阅地址: http://<本机IP>:%d/playlist.m3u8" % PORT)
    with socketserver.ThreadingTCPServer(("0.0.0.0", PORT), App) as srv:
        srv.serve_forever()

