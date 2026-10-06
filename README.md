# News Live｜不依赖Docker的Obsidian新闻Skill

让支持本地Skills、Python执行和联网阅读的AI助手，按需采集公开热榜与RSS，核验新闻原文，为你的工作、阅读和创作筛选最多3条重点，并保存到你指定的Obsidian新闻目录。

**不需要Docker、TrendRadar、采集API key或第三方Python包。**采集器使用Python3标准库；AI分析和原文核验依赖你正在使用的AI宿主与它的工具。它不是自带模型的独立新闻应用，也不会安装后自动定时运行。

## 工作方式

```text
公开热榜接口/RSS → Python保存原始快照与SQLite
                         ↓
                 AI阅读全文与外部核验
                         ↓
            结合关注主题与已有笔记去重、提出创作建议
                         ↓
             Obsidian每日新闻Markdown（同日只追加）
```

- 默认覆盖企业管理、AI应用、心理学，可在调用时改变关注方向。
- 选题不限关键词；能识别招聘、绩效、员工尊严和组织治理的实际问题。
- 每条提供为什么值得读、事实边界、工作/课程价值、创作形态与标题、核心论点、下一步验证，以及已有公开笔记的支持或挑战。
- 记录抓取开始/结束、上游缓存时间、报道发布时间及失败源；外部补充单独标记。
- 多主题素材只主收录一次；重复调用保留旧内容，只追加有价值增量。
- 数据不足不凑数；心理学弱信号明确说明，不做临床诊断或疗效推断。

## 安装

需要Python3.9+与IANA时区数据（`Asia/Shanghai`），可用网络，以及支持Skills、文件读写和联网搜索/正文阅读的AI宿主。多数macOS/Linux环境含时区数据；Windows或精简系统若报找不到时区，请先补齐系统时区数据或安装Python的tzdata。采集代码本身不需要第三方包。

### Codex

在尚未安装同名skill时：

```bash
git clone https://github.com/Jackyqian-ai/news-live.git "$HOME/.codex/skills/news-live"
```

已有同名skill时先备份本地修改和配置，再按自己的升级方式更新；不要直接覆盖。重新打开宿主会话以加载Skill，然后在对话中调用`$news-live`。

也可下载项目ZIP，将其中含SKILL.md、scripts、references和agents的目录放入宿主Skill目录，目录名保持`news-live`。其他宿主需自行确认其Skill发现路径与工具权限；本项目未声称在所有AI客户端完成兼容测试。

## 选择Obsidian库与归档目录

最简单的方式是在对话中明确指定，例如：

> 使用$news-live。我的Obsidian库是/path/to/MyVault，新闻存到1.输入/新闻资讯。关注HR实际AI工作链、组织管理和有原始证据的心理学。给出最多3条阅读重点与创作建议，同日已有文件只追加。

你可以改成自己的库内目录，例如`资讯/每日新闻`。首次未给出库且当前项目无法确认时，AI会询问；不会使用作者的个人路径。

需要以后继续使用相同位置时，保存本地配置：

```bash
python3 "$HOME/.codex/skills/news-live/scripts/configure.py" \
  --vault "/path/to/MyVault" \
  --news-dir "1.输入/新闻资讯" \
  --data-dir "9.系统/news-live-data"
```

创建`<vault>/.news-live.json`；库须已存在，配置脚本不会抓取新闻或创建分析笔记。默认三个主题目录由AI归档时建立。已有不同配置须明确加`--replace`才更新。

```json
{
  "vault": "/path/to/MyVault",
  "news_dir": "1.输入/新闻资讯",
  "data_dir": "9.系统/news-live-data",
  "topics": ["企业管理", "AI应用", "心理学"]
}
```

news_dir和data_dir支持库内相对路径或绝对路径，必须各自在选定库内且互不嵌套，以分开人读的资讯和原始数据。topics可按需要编辑成合法单层目录名，由AI读取；collector只使用数据路径，不生成分类笔记。身份、阅读偏好由调用指令或项目说明提供，不需要上传到GitHub。

若希望跨项目调用也采用默认位置，可在配置命令里加：

```bash
--config "$HOME/.codex/skills/news-live/config.local.json"
```

位置优先级：本次指令>Skill本地config.local.json>当前项目.news-live.json>已明确的Obsidian项目。config.local.json、.news-live.json都被.gitignore排除。

## 执行

### 完整AI工作流

在AI宿主中调用：

> $news-live，读取/path/to/MyVault/.news-live.json，获取最新新闻，并把核验后的创作建议归档。

最终笔记：

```text
<news-dir>/
├── 企业管理/YYYY-MM-DD-热点速览.md
├── AI应用/YYYY-MM-DD-热点速览.md
└── 心理学/YYYY-MM-DD-热点速览.md
```

日期采用北京时间。每篇新笔记含`来源: AI生成`、本批来源标记、真实新闻链接及已确认的相关wikilink；已有笔记保留原frontmatter和正文。当天每日工作项存在时按项目规则加入资讯链接，不存在不自动新建。仅新增输入笔记时不自动重写MOC。

### 只采集原始数据

```bash
python3 "$HOME/.codex/skills/news-live/scripts/collect.py" \
  --config "/path/to/MyVault/.news-live.json"
```

或独立选择原始数据位置：

```bash
python3 scripts/collect.py --output "/path/to/raw-news-data"
```

**--output只决定原始快照/数据库位置，不会把AI分析Markdown写入该目录。**只运行脚本不调用模型、不阅读全文、不生成创作建议。

定向复查与RSS时间范围：

```bash
python3 scripts/collect.py --output "/path/to/raw-news-data" \
  --sources thepaper,tmtpost,eeo --hours 24 --timeout 12
```

--sources为默认来源ID的逗号列表，不接受任意URL；--hours为1—168小时，--timeout为1—30秒。改变默认资料源需编辑HOTLISTS/FEEDS并核验解析格式；目前不提供任意网站通用爬虫。

## 资料源详细介绍

12个热榜通过NewsNow公共聚合服务取得；两个RSS直接请求源网站。它们适合不同的线索发现，热榜标题不等于事实核验结果。

| 类型 | 来源 | 主要用途 |
|---|---|---|
| 社区/公众热榜 | 知乎、微博、抖音、B站、百度热搜、今日头条、贴吧 | 公众事件、职场讨论、产品体验与创作线索；需回到原始来源核验 |
| 综合媒体热榜 | 澎湃新闻、凤凰网 | 社会报道、机构回应和公共治理 |
| 商业财经热榜 | 36氪、华尔街见闻、财联社 | 商业、科技产品、公司与产业事件 |
| 直接RSS | [钛媒体](https://www.tmtpost.com/feed) | 科技、商业、AI与深度评论 |
| 直接RSS | [经济观察报](https://www.eeo.com.cn/rss.xml) | 企业、产业、经济报道与案例 |

每个来源的ID、URL、时间字段、存储结构及限制见[完整采集说明](references/collection.md)。没有独立心理学学术订阅源；AI可使用宿主搜索补充原始论文并标明“外部补充”，不能把热榜说成学术覆盖。

## 能力边界与失败处理

- 完全不需要本地Docker或TrendRadar运行；仍依赖公共接口、RSS与网络。
- latest请求可能返回上游缓存；单次运行不是全天监控，也不能补回漏抓的历史榜单。
- 热榜通常只含标题、链接与顺序，RSS可能仅摘要；优先材料的全文由AI阅读工具获取，工具不可用就说明缺口。
- 来源可能返回500、403、限流或格式变化。终端JSON列出成功/失败源；退出码0只表示至少一个成功，2表示全失败，需继续检查快照。
- 独立SQLite按每次调用累计观察，不把出现次数当传播量，不写TrendRadar数据库。
- 不读取私人个案、督导、账号或凭据，不自动登录、发文、购买、发送消息或启用定时任务。
- 原始新闻与第三方内容不因本项目开源而获得转载许可；许可证仅覆盖本仓库代码及说明。

## 验证与项目文件

```bash
python3 -m unittest discover -s tests -v
```

测试覆盖缓存与发布时间分离、RSS时间边界、Atom链接、重复观察去重、自选配置路径和路径越界拒绝。单元测试不证明未来公共源可用；每次正式采集仍需检查source_status。

```text
SKILL.md                  AI工作流
scripts/collect.py        标准库采集器
scripts/configure.py      本地Obsidian位置配置
references/collection.md  全部来源与数据说明
agents/openai.yaml        Codex显示信息
tests/                    离线行为测试
```

默认源名单与公开接口参考：[NewsNow](https://github.com/ourongxing/newsnow)、[TrendRadar请求实现](https://github.com/sansan0/TrendRadar/blob/master/trendradar/crawler/fetcher.py)。采集器自行实现，未打包它们的程序或配置。

MIT许可证。欢迎报告失败源、解析变化或正文核验问题；不要在Issue中附私人配置、笔记、候选人资料或凭据。
