# 异世界日常系统 — 交付文档

## 项目概要

动漫风格的现实生活任务派送系统。每10分钟推送一条异世界主题内容到手机（ntfy），PC开机时附带语音播报（晓伊）。GitHub Actions 24小时云端运行，PC关机也不断。

## 快速启动

```powershell
# 1. 安装依赖
pip install schedule requests plyer pyttsx3 edge-tts

# 2. 配置手机推送
编辑 data/config.json → ntfy_topic 改为你的主题名

# 3. 手动运行
$env:PYTHONIOENCODING = "utf-8"
python main.py status        # 查看状态
python main.py daily          # 生成今日任务
python main.py weather        # 天气推送
python main.py fun now        # 随机趣味推送
python main.py voice test     # 语音测试
python main.py daemon start   # 启动本地守护进程
```

## 命令大全

### 基础日常
| 命令 | 说明 |
|------|------|
| `main.py daily` | 生成今日任务（1-4个动漫风格委托） |
| `main.py tasks list` | 列出活跃任务 |
| `main.py tasks complete <id>` | 完成任务，获得EXP/金币 |
| `main.py tasks expire_now <id>` | 手动过期任务 |
| `main.py tasks expired` | 查看已过期任务 |
| `main.py status` | 勇者状态面板 |
| `main.py set_state` | 更新心情/时间/勇气/阻塞因素 |
| `main.py add_place` | 添加地点 |
| `main.py add_npc` | 添加NPC |
| `main.py add_poi` | 添加兴趣点 |
| `main.py set_preference` | 修改偏好 |

### 旅行任务
| 命令 | 说明 |
|------|------|
| `main.py travel generate [--duration 60]` | 生成多站旅行任务 |
| `main.py travel steps <id>` | 查看步骤 |
| `main.py travel complete_step <id> <n>` | 完成步骤 |
| `main.py travel cancel <id>` | 取消旅行 |

### 奇遇故事线
| 命令 | 说明 |
|------|------|
| `main.py encounter on/off` | 开关奇遇推送 |
| `main.py encounter generate` | 生成奇遇任务 |
| `main.py encounter complete <id>` | 完成奇遇 |
| `main.py storyline list` | 故事线进度 |
| `main.py storyline reset <id>` | 重置故事线 |

### 语音播报
| 命令 | 说明 |
|------|------|
| `main.py voice test` | 测试语音（晓伊） |
| `main.py voice on/off` | 开关语音 |
| `main.py voice rate <100-300>` | 语速 |
| `main.py voice engine <pyttsx3\|edge-tts>` | 切换引擎 |

### 天气 & 趣味推送
| 命令 | 说明 |
|------|------|
| `main.py weather` | 天气推送（动漫风格） |
| `main.py weather set_city <城市>` | 设置天气城市 |
| `main.py fun now` | 随机趣味推送 |
| `main.py fun on/off` | 开关趣味推送 |

### 守护进程
| 命令 | 说明 |
|------|------|
| `main.py daemon start` | 启动守护进程（前台运行） |
| `main.py daemon stop` | 停止守护进程 |
| `main.py trigger location <name>` | 模拟位置触发 |

## 架构

```
用户
 ├── PC 开机 → Windows定时任务(每10分钟) → run_pc.py → 语音播报 + ntfy推送
 │              └── 开机启动项 → welcome.py → 开机欢迎语音
 │
 ├── PC 关机 → GitHub Actions(每10分钟) → run_once.py → ntfy推送
 │
 └── 手机 ← ntfy.sh ← 推送内容
```

### 双轨去重机制

PC 运行时每次推送后写入 `data/heartbeat.json` 并提交到 GitHub。GitHub Actions 检测到 9 分钟内有 PC 心跳则跳过，避免重复推送。

## 文件结构

```
my web/
├── main.py                     # CLI 入口
├── run_pc.py                   # PC 定时推送（带语音）
├── run_once.py                 # GitHub Actions 推送（无语音）
├── welcome.py                  # PC 开机欢迎语音
├── welcome.bat                 # 开机启动批处理
├── start_pc_daemon.bat         # 定时任务批处理
├── setup_welcome.ps1           # 开机启动安装脚本
├── fix_task.ps1                # 定时任务修复脚本
├── HANDOFF.md                  # 本文档
├── README.md                   # 项目说明
├── .gitignore
├── .github/workflows/
│   └── isekai-scheduler.yml    # GitHub Actions 工作流
├── core/
│   ├── __init__.py
│   ├── config.py               # JSON 配置加载
│   ├── content_gen.py          # 模板引擎（组合生成1800+条内容）
│   ├── encounter.py            # 奇遇故事线
│   ├── fun_content.py          # 12种趣味内容推送
│   ├── notifier.py             # ntfy + 桌面通知
│   ├── scheduler.py            # 守护进程
│   ├── task_manager.py         # 任务生成/完成/过期
│   ├── travel.py               # 旅行任务
│   ├── voice.py                # TTS 语音（pyttsx3 + edge-tts）
│   └── weather.py              # 天气获取（wttr.in）
└── data/
    ├── config.json             # ntfy话题、语音、天气、城市配置
    ├── user_state.json         # 等级/EXP/金币/心情
    ├── places.json             # 地点数据
    ├── npcs.json               # NPC数据
    ├── preferences.json        # 用户偏好
    ├── tasks.json              # 任务记录
    ├── pois.json               # 兴趣点
    ├── story_templates.json    # 故事模板
    ├── storylines.json         # 故事线进度
    ├── anime_words.json        # 动漫词库 + 模板词池（800+条目）
    ├── history.json            # 去重历史记录
    └── heartbeat.json          # PC 心跳（双轨去重）
```

## 配置说明 (data/config.json)

```json
{
  "ntfy_topic": "yishijie",               // ntfy.sh 主题名
  "ntfy_server": "https://ntfy.sh",
  "use_osm_api": false,
  "voice": {
    "enabled": true,
    "engine": "edge-tts",                  // pyttsx3 或 edge-tts
    "rate": 150,                           // 语速 100-300
    "volume": 1.0,
    "voice_id": "zh-CN-XiaoyiNeural",      // 语音角色
    "event_filters": ["new_task","weather","fun_content",...]
  },
  "idle_windows": ["12:00-13:30", "18:00-19:00"],
  "daemon": {
    "check_interval_minutes": 120,
    "push_if_tasks_less_than": 2
  },
  "weather": {"enabled": true, "city": "Changchun"},
  "fun_content": {"enabled": true}
}
```

### 语音角色选项

| voice_id | 描述 |
|----------|------|
| `zh-CN-XiaoxiaoNeural` | 晓晓 — 温暖活泼 |
| `zh-CN-XiaoyiNeural` | 晓伊 — 俏皮可爱 |
| `zh-CN-YunxiNeural` | 云希 — 男声自然 |
| `zh-CN-YunjianNeural` | 云健 — 成熟稳重 |
| `zh-CN-YunyangNeural` | 云扬 — 专业播音 |

## 推送内容类型（12种）

| 类型 | 标题 | 来源 |
|------|------|------|
| Micro Quest | 微挑战 | 模板引擎 |
| Life Tip | 勇者贴士 | 模板引擎 |
| Anime Quote | 动漫语录 | 模板引擎 |
| Kingdom News | 王国快讯 | 模板引擎 |
| Adventurer's Word | 冒险者一言 | 模板引擎 |
| Morning Blessing | 朝の祝福 | 模板引擎 |
| NPC Spotlight | NPC图鉴 | npcs.json |
| Place Discovery | 地点发现 | places.json |
| Fun Fact | 世界豆知识 | 固定池(19条) |
| Isekai Slang | 异世界黑话 | 模板引擎 |
| Isekai Recipe | 异世界食谱 | 模板引擎 |
| Isekai Motivation | 异世界激励 | 模板引擎 |

### 模板引擎说明

`core/content_gen.py` 使用组合模板生成海量唯一内容：
- 模板定义在 `_generate_type()` 的 `templates` 字典中
- 词池定义在 `data/anime_words.json`
- 去重通过 `data/history.json` 记录已使用哈希
- 每种类型独立去重，当前总容量 > 10,000 条

添加新内容类型步骤：
1. 在 `content_gen.py` 添加模板
2. 在 `anime_words.json` 添加词池
3. 在 `fun_content.py` 添加 `push_xxx()` 函数
4. 在 `push_random_fun()` 添加类型

## 部署指南

### 从零部署

```bash
# 1. 克隆
git clone https://github.com/ranwang0829-stack/yishijie.git
cd yishijie

# 2. 安装
pip install schedule requests plyer pyttsx3 edge-tts

# 3. 配置手机推送
# 编辑 data/config.json → ntfy_topic

# 4. 测试
python main.py status
python main.py voice test
python main.py fun now
```

### PC 定时任务

```powershell
# 安装（每10分钟）
python -c "
import subprocess, os
py = os.path.join(os.environ['LOCALAPPDATA'], 'Programs/Python/Python312/python.exe')
script = r'C:\Users\王\Desktop\my web\run_pc.py'
cmd = f'cmd /c \"{py}\" \"{script}\"'
subprocess.run(['schtasks','/create','/tn','IsekaiDailyPush','/tr',cmd,'/sc','minute','/mo','10','/f'])
"

# 删除
schtasks /delete /tn IsekaiDailyPush /f
```

### PC 开机欢迎

将 `welcome.bat` 的快捷方式放入：
`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\`

### GitHub Actions

推送代码到 GitHub 仓库后自动运行。工作流文件：
`.github/workflows/isekai-scheduler.yml`

调整频率：修改 `cron` 表达式。

## 依赖

| 库 | 用途 | 必需 |
|----|------|------|
| `requests` | ntfy推送 + 天气API | 是 |
| `schedule` | 守护进程定时 | PC端 |
| `plyer` | 桌面弹窗 | PC端 |
| `pyttsx3` | 离线语音 | PC端 |
| `edge-tts` | 在线自然语音 | PC端 |
| `asyncio` | edge-tts依赖 | PC端 |

## 静默时段

推送时段：每天 **08:00 ~ 次日 02:00**（北京时间）
静默时段：**02:00 ~ 08:00**（不推送）

代码位置：`run_pc.py` 和 `run_once.py` 的 `if 2 <= hour < 8: return`

## 故障排除

| 问题 | 解决 |
|------|------|
| 手机收不到推送 | 打开ntfy应用→下拉刷新；检查通知权限；关闭电池优化 |
| 语音没声音 | `python main.py voice test` 测试；检查音量；确认edge-tts已安装 |
| PC定时任务不运行 | 运行 `fix_task.ps1`；检查任务计划程序 |
| 推送内容重复 | 检查 `data/history.json`；去重依赖此文件 |
| GitHub Actions不触发 | 确认推送到main分支；检查Actions页面 |
| 天气获取失败 | 检查网络；城市名用拼音（如Changchun） |

## 版本历史

- v1.0 — 基础日常任务 + 旅行 + 奇遇 + 语音
- v1.1 — 天气推送 + 趣味内容
- v1.2 — 模板引擎（10,000+ 组合内容）
- v1.3 — 双轨并行（PC语音 + GitHub云端）
- v1.4 — 12种推送类型 + MCI静默语音 + 去重系统
