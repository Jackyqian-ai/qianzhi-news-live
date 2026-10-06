# 资料源、采集格式与边界

## 14个默认来源

前12项通过同一个NewsNow公开聚合接口请求，并非分别直连12个网站的爬虫：`https://newsnow.busiyi.world/api/s?id=<ID>&latest`。下表“适合发现”是选题用途，不是覆盖保证或官方榜单定义；返回条数、榜单内容与可用性由上游决定。

| ID | 来源 | 适合发现 | 读取方式 |
|---|---|---|---|
| zhihu | 知乎 | 职场争论、组织议题、AI使用反馈 | NewsNow热榜 |
| weibo | 微博 | 公众事件、公司回应、员工尊严线索 | NewsNow热榜 |
| douyin | 抖音 | 大众关注事件、视频传播话题 | NewsNow热榜 |
| bilibili | B站 | AI演示、知识视频、创作者议题 | NewsNow热榜 |
| baidu | 百度热搜 | 综合社会与公司新闻 | NewsNow热榜 |
| toutiao | 今日头条 | 综合新闻、劳动与管理事件 | NewsNow热榜 |
| tieba | 贴吧 | 社区反应、职场讨论线索 | NewsNow热榜 |
| thepaper | 澎湃新闻 | 社会报道、机构回应、公共治理 | NewsNow热榜 |
| ifeng | 凤凰网 | 综合时事与商业新闻 | NewsNow热榜 |
| 36kr-renqi | 36氪 | 创业、产品、商业与AI公司 | NewsNow热榜 |
| wallstreetcn | 华尔街见闻 | 宏观、公司、科技商业 | NewsNow热榜 |
| cls | 财联社 | 财经、公司与产业信息 | NewsNow热榜 |
| tmtpost | 钛媒体 | 商业、科技、管理与AI深度文章 | 直接RSS：https://www.tmtpost.com/feed |
| eeo | 经济观察报 | 企业、产业、经济与组织案例 | 直接RSS：https://www.eeo.com.cn/rss.xml |

论坛与短视频讨论只能作为线索，不能当研究样本。当前没有独立心理学论文订阅源；心理学强信号不足时，AI应通过宿主搜索核验原始研究，标外部补充，不能将综合热榜等同专业学术覆盖。

## 内容与时间

热榜条目保存标题、URL、榜内顺序、source_id、collected_at、upstream_updated_at、upstream_status。接口不提供文章发布时间时保存为空；不拿缓存更新时间替代它。RSS保存标题、URL、最多2500字符的摘要、published_at、published_raw、publication_status；RSS/Atom不保证全文。

RSS默认24小时，可用`--hours 1..168`调整。明确时区的旧条目过滤；缺日期、缺时区、未来时间保留并标记，不将其当已发生近期报道。Atom仅有updated、不含published时，不自动将修改时间当首次发表时间。

默认最多4并发、每源2次请求、每请求12秒超时、单响应4MB上限；400类错误中除408/429不重试。返回0表示至少一个来源成功，不等于全部成功或有文章；全源失败返回2。必须检查successful_sources/failed_sources及快照的完整source_status。

`latest`仍可返回cache。热榜排名是本来源当前顺序，不支持跨平台“最热”排序；items数量和数据库observation_count不是阅读量、全网传播量或全天热度。单次采集无法恢复停机期间错过的热榜。

## 输出

```text
<data-dir>/YYYY-MM-DD/
├── HHMMSS-随机ID/
│   ├── snapshot.json
│   └── raw/               # 每来源的JSON/XML响应
└── news-live.sqlite3
```

SQLite包含runs、source_status、items、observations。items按来源与URL去重，同条目同次调用只计一次观察；同事件跨来源由AI分析合并，保留不同来源的佐证。配置与日志中的本地路径不要提交公开仓库。

脚本自行实现HTTP请求、解析和存储，未复制TrendRadar源码。公开接口与ID依据：[TrendRadar请求实现](https://github.com/sansan0/TrendRadar/blob/master/trendradar/crawler/fetcher.py)、[NewsNow来源清单](https://github.com/ourongxing/newsnow/blob/main/shared/sources.json)。本项目不打包这两个上游项目，不要求启动它们。公共服务的限流、DNS、缓存、接口变动或停机仍会影响结果；不可将Docker独立性当网络独立性。
