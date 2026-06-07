# 异世界日常系统 (Isekai Daily Quest System)

一个动漫风格的现实生活任务派送系统。将日常生活游戏化，生成带有时限的"委托任务"，鼓励用户探索周边、与人互动、完成小目标，并通过语音播报和手机通知实时推送。

## 功能概览

- **基础日常任务**：根据心情、距离、社交勇气等参数自动生成每日任务（对话、探索、拍照、观察、善意动作等）
- **旅行任务**：多步骤路线型微旅行，串联兴趣点(POI)，支持 OpenStreetMap 自动发现
- **奇遇故事线**：串联式社交任务，引导与陌生人的有意义的短暂互动
- **语音播报**：pyttsx3（离线）或 edge-tts（在线），关键事件自动朗读
- **双重通知**：ntfy.sh 手机推送 + 桌面弹窗（plyer）
- **后台守护进程**：定时检查、自动补发任务、过期清理
- **等级系统**：经验值/金币/称号，完成任务获得成长

## 系统要求

- Python 3.9+
- Windows / macOS / Linux

## 安装

```bash
# 1. 克隆或下载项目
cd "my web"

# 2. 安装核心依赖
pip install schedule requests plyer pyttsx3

# 3. 可选依赖
pip install edge-tts        # 更自然的在线语音（需要网络）
```

## 快速开始

```bash
# 查看帮助
python main.py help

# 查看勇者状态
python main.py status

# 更新今日状态（心情、可用时间等）
python main.py set_state

# 生成今日任务
python main.py daily

# 查看活跃任务
python main.py tasks list

# 完成任务
python main.py tasks complete <任务ID>

# 测试语音
python main.py voice test
```

## 命令详解

### 基础日常任务

| 命令 | 说明 |
|------|------|
| `daily` / `generate` | 根据当前状态生成今日任务 |
| `tasks list` | 列出活跃任务（按剩余时间排序） |
| `tasks complete <id>` | 完成任务，获得经验/金币 |
| `tasks expire_now <id>` | 手动过期任务 |
| `tasks expired` | 查看已失效任务 |
| `set_state` | 交互式更新心情/时间/勇气/阻塞因素 |
| `add_place` | 添加新地点 |
| `add_npc` | 添加新 NPC |
| `set_preference` | 修改偏好设置 |
| `status` | 查看勇者完整状态 |

### 旅行任务

| 命令 | 说明 |
|------|------|
| `travel generate [--duration 60]` | 生成多站旅行任务（时长30-120分钟） |
| `travel steps <id>` | 查看旅行步骤详情 |
| `travel complete_step <id> <n>` | 完成第 n 个步骤（0-indexed） |
| `travel cancel <id>` | 取消旅行任务 |
| `add_poi` | 添加兴趣点(POI) |

### 奇遇与故事线

| 命令 | 说明 |
|------|------|
| `encounter on` / `encounter off` | 开关奇遇推送 |
| `encounter generate [location]` | 生成奇遇任务 |
| `encounter complete <id>` | 完成奇遇，推进故事线 |
| `storyline list` | 查看故事线进度 |
| `storyline reset <id>` | 重置故事线 |

### 语音播报

| 命令 | 说明 |
|------|------|
| `voice on` / `voice off` | 开关语音 |
| `voice test` | 测试语音播报 |
| `voice rate <100-300>` | 设置语速 |
| `voice engine <pyttsx3\|edge-tts>` | 选择语音引擎 |

### 后台守护进程

| 命令 | 说明 |
|------|------|
| `daemon start` | 启动守护进程（定时检查+自动推送） |
| `daemon stop` | 停止守护进程 |

### 位置触发

| 命令 | 说明 |
|------|------|
| `trigger location <name>` | 模拟到达某地点，立即生成关联任务 |

## 配置说明

编辑 `data/config.json`：

```json
{
  "ntfy_topic": "your_topic_here",     // ntfy.sh 主题名
  "ntfy_server": "https://ntfy.sh",     // 自建 ntfy 服务器地址
  "use_osm_api": false,                 // 是否启用 OpenStreetMap POI 查询
  "voice": {
    "enabled": true,
    "engine": "pyttsx3",               // pyttsx3 或 edge-tts
    "rate": 150,                        // 语速 100-300
    "volume": 1.0,
    "voice_id": "",                     // 留空=默认，可指定语音ID
    "event_filters": ["new_task", "task_expiring", "task_complete", "level_up", "storyline_chapter"]
  },
  "idle_windows": ["12:00-13:30", "18:00-19:00"],  // 空闲时段（任务生成加成）
  "daemon": {
    "check_interval_minutes": 120,      // 守护进程检查间隔
    "push_if_tasks_less_than": 2        // 活跃任务低于此数时自动生成
  }
}
```

### ntfy.sh 手机通知配置

1. 在手机上下载 [ntfy](https://ntfy.sh/) 应用
2. 在应用中订阅一个**独一无二**的主题名（如 `my_isekai_quest_abc123`）
3. 将主题名填入 `data/config.json` 的 `ntfy_topic` 字段
4. 运行 `python main.py daily` 测试，手机应收到推送

### OSM API 配置（可选）

1. 在 `config.json` 中设置 `"use_osm_api": true`
2. 生成旅行任务时传入坐标：`python main.py travel generate --lat 39.9042 --lon 116.4074`
3. 系统将自动查询周围 3km 内的非商业兴趣点

## 数据文件

所有数据存储在 `data/` 目录下的 JSON 文件中：

| 文件 | 用途 |
|------|------|
| `user_state.json` | 勇者状态（等级/经验/金币/心情等） |
| `places.json` | 地点列表 |
| `npcs.json` | NPC 人物列表 |
| `preferences.json` | 用户偏好 |
| `tasks.json` | 所有任务记录 |
| `pois.json` | 兴趣点(POI) |
| `story_templates.json` | 故事线模板 |
| `storylines.json` | 进行中的故事线进度 |
| `anime_words.json` | 动漫风格词库 |
| `config.json` | 系统配置 |

首次运行时，若文件不存在会自动创建并填入示例数据（3+地点、4+NPC、7个POI、3条故事线）。

## 项目结构

```
├── main.py                 # 入口，命令行解析
├── README.md
├── core/
│   ├── __init__.py
│   ├── config.py           # 配置加载/保存
│   ├── task_manager.py     # 任务生成、完成、过期
│   ├── notifier.py         # ntfy + plyer 通知
│   ├── voice.py            # TTS 语音播报
│   ├── scheduler.py        # 后台守护进程
│   ├── travel.py           # 旅行任务
│   └── encounter.py        # 奇遇+故事线
└── data/
    └── *.json              # 数据文件
```

## 依赖列表

| 库 | 用途 | 必需 |
|----|------|------|
| `schedule` | 守护进程定时 | 是 |
| `requests` | ntfy推送 + OSM API | 是 |
| `plyer` | 桌面弹窗通知 | 是 |
| `pyttsx3` | 离线语音播报 | 是 |
| `edge-tts` | 在线高质量语音 | 否 |
| `asyncio` | edge-tts 依赖 | 否 |

## 跨平台说明

- 路径使用 `pathlib`，兼容 Windows/macOS/Linux
- 音频播放：Windows 使用 PowerShell Media.SoundPlayer，macOS 使用 afplay，Linux 尝试 mpv/ffplay/aplay/paplay
- 桌面通知：plyer 封装了各平台原生通知

## 故障排除

- **语音无声**：检查 `config.json` 中 `voice.enabled` 是否为 `true`，确认 pyttsx3 已安装
- **手机收不到推送**：确认 `ntfy_topic` 设置正确且手机已订阅同一主题
- **edge-tts 报错**：确认网络连接正常，或切换回 `pyttsx3` 引擎
- **OSM 查询超时**：Overpass API 是公共服务，偶有延迟，稍后重试
- **plyer 通知不显示**：Linux 需要 `libnotify`，macOS 需授权通知权限
