# Novel Insight · 网文人情世故分析工具

本地运行的网页应用:投入一本网络小说(txt/epub),自动按章节切分、过滤低密度章节、调用 LLM 做**人情世故(行为层 6 维)**与**对话技巧(逐句精读)**分析,产出结构化的「做派卡」「对话卡」知识库,并跨章节聚合出人物画像、情境聚类、长期账时间线。单用户本地使用,数据存本地 SQLite,可一键导出 Markdown。

---

## 一、环境要求

- Python 3.11+
- Node.js 18+(构建/开发前端用)
- 一个 LLM API Key(默认 DeepSeek,兼容 OpenAI/Claude)

## 二、目录结构

```
novel-insight/
├── app/                # 后端(FastAPI)
│   ├── main.py         # 入口:挂载 API + WebSocket + 静态前端
│   ├── config.py       # 配置(读 .env)
│   ├── core/           # 文本加载 / 章节切分 / 密度过滤
│   ├── llm/            # LLM 抽象层 + DeepSeek 实现 + Prompt
│   ├── analyzers/      # 行为分析 / 对话抽取 / 对话精读 / 聚合
│   ├── db/             # 模型 / 引擎 / CRUD(SQLAlchemy async)
│   ├── api/            # 路由(books/analysis/results/export)
│   └── services/       # 流程编排(book / analysis / 进度推送)
├── frontend/           # 前端(Vue3 + Element Plus + Vite)
└── data/
    ├── books/          # 上传的原始 txt/epub
    ├── novel_insight.db
    └── exports/
```

## 三、安装

### 后端

```powershell
cd novel-insight
python -m venv .venv
.venv\Scripts\Activate.ps1          # PowerShell;CMD 用 .venv\Scripts\activate.bat
pip install -r requirements.txt
```

### 前端

```powershell
cd frontend
npm install
```

## 四、配置 .env

复制示例并填入 API Key(**代码里不存任何 Key,一律从 .env 读**):

```powershell
copy .env.example .env        # 已有 .env 则跳过
```

关键项:

| 变量 | 说明 |
|---|---|
| `LLM_PROVIDER` | `deepseek` / `openai` / `claude`,切换 provider 只改这里 |
| `DEEPSEEK_API_KEY` | **必填**,你的 DeepSeek Key |
| `DEEPSEEK_FAST_MODEL` | 行为层用,默认 `deepseek-chat`(V3,支持 JSON mode) |
| `DEEPSEEK_DEEP_MODEL` | 对话精读用,默认 `deepseek-reasoner`(R1) |
| `LLM_CONCURRENCY` | 并发上限,默认 5 |
| `LLM_TIMEOUT` | 单次调用超时秒数,默认 120 |
| `LLM_MAX_RETRIES` | 失败重试次数,默认 3(指数退避 1/2/4s) |
| `DENSITY_THRESHOLD` | 密度阈值,≥ 此值才送分析,默认 30(可调) |

## 五、启动

### 方式 A:单端口(推荐,贴近 http://localhost:8000)

先构建前端,再起后端,前端由后端直接托管:

```powershell
cd frontend; npm run build; cd ..
.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

浏览器打开 **http://localhost:8000**。

### 方式 B:开发模式(前后端分离,热更新)

```powershell
# 终端 1:后端
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
# 终端 2:前端(自动代理 /api 与 /ws 到 8000)
cd frontend; npm run dev
```

浏览器打开 **http://localhost:5173**。

## 六、使用流程

1. **投书**:首页「投书」拖入 txt/epub → 自动切分,显示总章节数、平均字数、密度分布直方图。
2. **分析**:点「一键启动分析」。进度条通过 WebSocket 实时更新(当前章节、已完成/失败数、预计剩余)。
3. **浏览**:
   - 书籍详情页:左侧章节树(低密度章节灰显),点章看行为分析 + 对话精读。
   - 做派卡墙:按维度 / 标签 / 人物筛选;每张卡含本章「社会规则」。
   - 对话卡墙(主角发言为核心):按**场景**(酒桌/道歉/谄媚/站队…)/ 技巧 / 说话者 / 表态强度筛选。每张卡含:**潜台词**、**话术结构**(先说什么→再说什么,每步目的)、逐句拆解。
   - **社会规则 / 潜规则手册**:跨章提炼去重的"没人教就不懂"的社会常识,按官场/酒桌/人情往来等分类。
   - 人物画像:每个人物的处世模式 + 出场场景时间线。
   - 情境聚类 & 长期账:同类情境的共性打法 + 人情债时间线。
4. **导出**:详情页「导出」下载整本 Markdown 压缩包;也可按标签 / 按人物单独导出。

## 七、断点续传

- 分析任务支持中途中止 / 继续:`Chapter.analysis_status` 记录每章状态(pending/analyzing/completed/failed/skipped)。
- 服务**重启时自动**把残留的 `analyzing` 章节回滚为 `pending`,下次「继续分析」从断点续跑,不会从头再来。
- 单章失败(重试耗尽或 JSON 解析失败)只标记该章 `failed` 并把原始响应存库(`raw_response`,调试用),**不中断整体流程**;完成后可「重跑失败章」。

## 八、数据与备份

- SQLite 文件:`data/novel_insight.db`。直接复制此文件即完成备份;恢复时覆盖回去即可。
- 原始书籍文件:`data/books/`。
- 导出的 Markdown:浏览器下载,不落 `data/exports/`(该目录预留)。
- 全文检索基于 SQLite FTS5(中文用 jieba 分词),随库自动维护。

## 九、已知问题 / 注意事项

- **本机 Clash 代理坑**:若 `localhost:8000` 返回 502,是系统代理(Clash TUN)劫持了本地请求。把 `127.0.0.1` / `localhost` 加入代理绕过列表即可;浏览器一般默认绕过 localhost,问题主要出现在命令行工具。
- **密度过滤对纯对话型都市文几乎不拦截**:这类书章章有人物互动,通过率本就高(正常)。若想多省 token,调高 `DENSITY_THRESHOLD`。密度过滤真正省钱体现在玄幻/打怪章节多的书上。
- **R1(deepseek-reasoner)不支持 JSON mode**:对话精读靠后处理从响应中提取 JSON,已做容错(去 ```json``` 包裹、尾随逗号修复);极端格式错乱时该段对话跳过,不影响行为卡。
- **对话精读较慢且耗 token**:每章最多抽 5 段主角长对话送 R1,一本大书可能上千次 R1 调用,请留意配额。
- 维度 Prompt 聚焦**当代都市/职场/商战**语境;武侠/玄幻/古代背景的章节分析价值有限。

## 十、验证记录(Day 1)

以一本长篇都市网文(374 章,约 78 万字)为测试样本:

- 切分:正则命中 374 处「第X章」,连续编号 1→374,过滤短章节后 374 章,平均 2083 字/章。
- 密度:均值 88,373/374 章达标(阈值 30);分布 `{20-30:1, 30-40:5, 40-50:9, 50-60:32, 60-70:23, 70-80:31, 80-90:29, 90-100:244}`。
- API:`POST /api/books/upload` 返回上述统计;`GET /api/books/{id}/chapters`、`/progress` 正常。
- 前端:书架、详情页、章节列表(密度灰显)渲染正常,WebSocket 进度通道与 Vite 代理工作正常。
