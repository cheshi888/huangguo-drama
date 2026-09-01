# 黄果短剧解析与播放

爬取 [huangguoai.com](https://huangguoai.com) 短剧，并提供本地播放面板 + 订阅服务。

## 文件说明

| 文件 | 作用 |
|------|------|
| `huangguo_parser.py` | 解析首页 / 分类 / 搜索 / 详情 / 播放地址 |
| `crawl_update.py` | 增量爬取全站剧集（只爬新增，不重复） |
| `player_server.py` | 本地播放面板（网页） + 订阅服务（m3u8） |
| `export_m3u.py` | 从爬取结果导出 m3u8 播放列表 |
| `start.py` / `start.bat` | 一键启动 |

## 使用

```bat
start.bat              # 启动播放面板（http://127.0.0.1:8788/）
python start.py update # 增量更新
```

## 订阅地址

```
http://<本机IP>:8788/playlist.m3u8
```

## 说明

视频播放地址带时效性签名（`auth_key`），过期后会失效。
因此播放时通过 `/api/stream`（网页面板）或 `/play`（订阅代理）实时解析，
拿到新鲜签名后再播放，避免链接过期。
