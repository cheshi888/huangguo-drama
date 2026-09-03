# 黄果短剧解析与播放

爬取 [huangguoai.com](https://huangguoai.com) 短剧，提供本地播放面板 + 订阅服务，并常驻后台定时刷新播放地址、自动抓取新剧。

## 文件说明

| 文件 | 作用 |
|------|------|
| `huangguo_parser.py` | 解析首页 / 分类 / 搜索 / 详情 / 播放地址 |
| `crawl_update.py` | 增量爬取 + 刷新播放地址 |
| `daemon.py` | 常驻守护进程：定时刷新地址 + 自动抓新剧 |
| `player_server.py` | 本地播放面板（网页） + 订阅服务（m3u8） |
| `export_m3u.py` | 从爬取结果导出 m3u8 播放列表 |
| `start.py` / `start.bat` | 一键启动（Windows） |
| `deploy.sh` | Linux VPS 一键部署（systemd 常驻 + 开机自启） |

## 使用

```bat
start.bat              # 一键启动：后台常驻守护 + 播放面板（http://127.0.0.1:8788/）
python start.py update # 手动增量更新
```

## VPS 部署（Linux）

把整个目录上传到 VPS，然后执行：

```bash
sudo bash deploy.sh
```

脚本会自动：检测 Python3 → 生成 systemd 服务 → 开机自启 + 常驻运行。

部署后访问：
- 播放面板：`http://<VPS公网IP>:8788/`
- 订阅地址：`http://<VPS公网IP>:8788/playlist.m3u8`

常用命令：
```bash
systemctl status huangguo      # 查看状态
journalctl -u huangguo -f     # 实时日志
systemctl restart huangguo    # 重启
```

> 只需 Python3（无需任何第三方库）。如无法访问请放行防火墙端口 8788。

## 订阅地址

```
http://<本机IP>:8788/playlist.m3u8
```

## 常驻守护（防过期）

守护进程默认每 **30 分钟**检查一次：并行扫描抓取新增剧集，并对「签发超过 30 分钟」的播放地址重新抓取，保证订阅里的地址始终新鲜。

为提速：
- 日常检查用「快速扫描」——每个分类只扫前 3 页（几秒~十几秒完成）
- 每隔 12 轮（约 6 小时）做一次全站全量扫描，确保不漏掉排在后面的新剧
- 扫描、抓剧、刷新地址均为多线程并行

可通过环境变量调整：
- `REFRESH_MINUTES`：检查间隔（分钟，默认 30）
- `REFRESH_AGE_SECONDS`：地址签发超过多少秒就重新抓（默认 1800）
- `SCAN_LIMIT`：每轮每个分类最多扫多少页（默认 3）
- `FULL_SCAN_EVERY`：每多少轮做一次全量扫描（默认 12）
- `CRAWL_WORKERS`：并发线程数（默认 12）

## 说明

视频播放地址带时效性签名（`auth_key`），过期后会失效。
因此由守护进程定时刷新；网页面板另提供 `/api/stream` 实时取流兜底。

