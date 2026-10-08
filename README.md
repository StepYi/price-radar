# PriceRadar · 每日顶刊价格研究雷达

每天自动从 **17 本价格研究顶刊**里，挑出 **10 篇最相关的新文章**，生成一份可搜索的
HTML 看板和 Markdown 日报。零第三方依赖（纯 Python 标准库），不需要任何 API Key 就能跑。

```powershell
cd price-radar
python -m priceradar resolve      # 首次：解析期刊（约 20 秒）
python -m priceradar run --open   # 生成并打开今天的日报
.\share.ps1                       # 想让同事也能看？起个局域网服务器
```

---

## 1. 它长什么样

生成的 `data/out/index.html` 是一个深色看板，包含：

| 元素 | 作用 |
| --- | --- |
| 综合分 + 排名 | 每篇文章一个 0–100 分，可解释（见第 5 节） |
| 期刊 / 上线时间 / 等级 | `上线 2026-10-08（0 天前）· 在线 2026-10-01` |
| 摘要（可展开） | 有摘要的直接读，没有的会明确标注 |
| 关键词标签 | 命中的价格词 / 商品词，一眼看出为什么推它 |
| **为什么推荐** | 相关性、期刊权重、时效、方法匹配四栏打分明细 |
| 一键直达 | DOI 原文 / 开放获取全文 / OpenAlex |
| 搜索框 | 按 `/` 聚焦，按标题、摘要、作者、关键词实时过滤 |
| 方向筛选 | 金融经济 / 能源资源 / 农业商品 / 计量预测 |
| 历史日报 | 左侧列出最近 30 天，点进去看往期 |

每次运行产出这一整套文件：

| 文件 | 用途 |
| --- | --- |
| `index.html` | **看板首页**，永远指向最新一期 |
| `2026-10-08.html` | 当天看板（可直接发给别人，单文件自包含） |
| `2026-10-08.md` | Markdown 版（发邮件、粘笔记） |
| `feed.xml` | **RSS 订阅源**，别人用阅读器订阅一次就天天自动收到 |
| `2026-10-08.json` | 结构化数据（对接你自己的系统） |
| `latest.md` | 永远是最新一期 |

---

## 2. 让别人也能看（重点）

**默认只能你自己看。** `index.html` 是通过 `file://` 在本地打开的，路径长这样：

```
file:///C:/Users/你/Documents/.../price-radar/data/out/index.html
```

把这个路径发给同事没用 —— 文件在他们电脑上不存在。要给出去，必须有一个**网址**。
下面三种方式，按「范围」从小到大：

### 方式 1：局域网共享（30 秒搞定，适合同办公室）

在你电脑上起一个小服务器，同事在同一个 WiFi / 办公网里用浏览器直接打开就行，
**他们不需要装 Python，也不需要拿到任何文件**：

```powershell
.\share.ps1
```

脚本会自己找你的局域网 IP、尝试放行防火墙，然后打印出同事要用的地址：

```
  本机打开      http://127.0.0.1:8080/
  分享给同事    http://10.47.159.39:8080/
```

同事在浏览器输入 `http://10.47.159.39:8080/` 就能看到，手机也行。
**只要你的电脑开着、脚本在跑，他们就能看。** 按 `Ctrl+C` 停止分享。

换成手写命令也一样：

```powershell
python -m priceradar serve            # 默认 8080，允许局域网访问，会打印分享地址
python -m priceradar serve -o         # 顺便打开浏览器
python -m priceradar serve --local    # 只允许本机（不想给别人看时）
python -m priceradar serve --port 9000
```

> **同事打不开怎么办？** 九成是 Windows 防火墙。用**管理员** PowerShell 执行一次：
> ```powershell
> netsh advfirewall firewall add rule name="PriceRadar 8080" dir=in action=allow protocol=TCP localport=8080
> ```
> 另外要确认你们在同一个网段、且你的网络配置文件不是「公用网络」（公用网络默认禁止入站）。

**优点**：0 成本、0 配置、数据不出你的电脑。
**缺点**：只能同网络；你的电脑关机或休眠就断了；IP 可能变化（路由器重启后会变）。

### 方式 2：GitHub Pages（推荐，得到一个永久公网网址）

任何人都能看，不需要你的电脑开着，免费、自动 HTTPS。我已在
`.github/workflows/daily.yml` 里写好了一个 **可选** 的 `pages` 任务。

步骤：

1. 把整个 `price-radar` 目录推到一个 GitHub 仓库（公开或私有都行）。
2. 仓库 **Settings → Secrets and variables → Actions → Secrets**，添加：
   - `PRICERADAR_MAILTO` = 你的邮箱（**必填**，否则 Unpaywall 拒服务）
   - `OPENALEX_API_KEY` = 你的 OpenAlex Key（可选，但能补上 Elsevier 摘要）
3. 仓库 **Settings → Pages → Source** 选 **GitHub Actions**。
4. 仓库 **Settings → Secrets and variables → Actions → Variables**，
   新建一个变量 `ENABLE_PAGES` = `true`（这一步是「开关」，不加就不发布，避免没配好时任务变红）。
5. 在 **Actions** 页面手动点一次 `Run workflow`。

跑完后你会得到一个固定网址：

```
https://你的用户名.github.io/price-radar/
```

把这个链接发给任何人都能打开。之后每天定时任务自动抓取 → 提交 → 自动更新看板。
订阅源是 `https://你的用户名.github.io/price-radar/feed.xml`。

> 不想公开？仓库设为 **Private** 即可，Pages 可以设置成仅自己可见（需要 GitHub Pro），
> 或者改用方式 3 的 Cloudflare Pages + Access。
>
> 另外：如果你不想用 Actions 发布，也可以走**分支模式** ——
> Settings → Pages → Source 选 `Deploy from a branch` → 分支 `main` → 目录 `/ (root)`。
> 仓库根目录的 `index.html` 会自动跳转到 `data/out/index.html`，网址同样是
> `https://你的用户名.github.io/price-radar/`。定时任务本来就会把 `data/out` 提交回仓库。

### 方式 3：Cloudflare Pages / Netlify（拖拽上传，最快看到效果）

不想碰 Git 的话，这两个都支持**直接把文件夹拖进网页**就发布：

1. 打开 <https://pages.cloudflare.com> 或 <https://app.netlify.com/drop>
2. 把电脑上的 `price-radar\data\out` 这个**文件夹**直接拖进去
3. 几秒后得到一个网址，例如 `https://price-radar.pages.dev`

想看最新内容时，重新拖一次即可（或者接上 Git 仓库让它自动部署）。
Cloudflare Pages 免费额度很大，还能绑自己的域名、给页面加访问密码。

### 方式 4：让别人「订阅」而不是每天来点链接

日报每次都会生成 `feed.xml`（RSS 2.0，含最近 20 期共 200 条）。只要你用方式 2 或 3
把它挂到公网，同事就能用任何阅读器订阅：

- 网页版：[Feedly](https://feedly.com)、[Inoreader](https://www.inoreader.com)
- 桌面/手机：NetNewsWire、Reeder、Thunderbird、Outlook（都支持 RSS）
- 国内：任何支持 RSS 的阅读器

订阅地址形如 `https://你的网址/feed.xml`。**这是最省事的分发方式** ——
你只管生产，别人自己订阅，不用你每次转发。

> 记得在 `config.toml` 里把 `public_url` 填成你的公网地址，
> 否则 RSS 里的自引用链接会指向 `localhost`。

### 方式 5：共享网盘（最土但能用）

`index.html` 和 `2026-10-08.html` 都是**单文件自包含**的（CSS/JS 全内联，不依赖任何外部资源），
所以直接丢进 OneDrive / 坚果云 / 企业微信群的共享文件夹，别人下载后双击就能看。
缺点是历史归档之间的跳转链接会失效（`index.html` → 其他日期），当期内容完全正常。

### 方式对比

| 方式 | 谁能看 | 要我的电脑开着吗 | 成本 | 适合 |
| --- | --- | --- | --- | --- |
| 局域网 `share.ps1` | 同一网络的人 | ✅ 要 | 0 | 同办公室同事、手机上临时看 |
| GitHub Pages | 任何人（或仅自己） | ❌ 不用 | 0 | 长期分享、发链接给外部合作者 |
| Cloudflare Pages | 任何人 | ❌ 不用 | 0 | 不想用 Git、想加访问密码 |
| RSS 订阅 | 订阅了的人 | ❌ 不用 | 0 | 让同事自己订阅，最省事 |
| 共享网盘 | 拿到文件的人 | ❌ 不用 | 0 | 一次性发给某个人 |

---

## 3. 覆盖的期刊（17 本，四类）

| 方向 | 期刊 | 权重 |
| --- | --- | --- |
| **金融经济** | Journal of Finance、Journal of Financial Economics、Review of Financial Studies、American Economic Review、Quarterly Journal of Economics、Econometrica、Management Science | 1.22–1.30 |
| **能源资源** | Energy Economics、The Energy Journal、Journal of Environmental Economics and Management、Resource and Energy Economics | 1.00–1.25 |
| **农业商品** | American Journal of Agricultural Economics、Journal of Commodity Markets、Food Policy | 0.95–1.25 |
| **计量预测** | Journal of Econometrics、International Journal of Forecasting、Journal of Forecasting | 0.95–1.15 |

加刊只要在 `config.toml` 里复制一段 `[[journal]]`，然后 `python -m priceradar resolve --refresh`。

---

## 4. 数据源选型（这一节很重要）

我在真实测试中确认了 2026 年各接口的现状，架构是按这些事实设计的：

| 数据源 | 角色 | 覆盖 | 成本 |
| --- | --- | --- | --- |
| **Crossref** | 主干：发现 + 标题/作者/DOI/期号/被引 | 17/17 本，按 ISSN 精确到刊 | 免费无限（建议填 `mailto` 进 polite pool） |
| **ScienceDirect TOC RSS** | 补 Elsevier 的精确在线日期与原文链接 | Elsevier 6 本 | 免费 |
| **Semantic Scholar** | 批量补摘要 + 免费全文链接（一次查 200 个 DOI） | 新文章覆盖一般 | 免费（未配 Key 时限流，已做退避） |
| **Unpaywall** | 为打分靠前的文章找**合法**免费全文 | 全部 | 免费，**必须填真实邮箱** |
| **OpenAlex** | 摘要质量最高的增强层 | 全部 | ⚠️ 见下 |

### ⚠️ 关于 OpenAlex 的坑（实测踩到）

OpenAlex 2026 年起改成了**按额度计费**。不带 Key 的请求消耗「同一 IP 共享的每日免费预算
（约 100 次请求）」，被别的程序用光后你会直接收到：

```
HTTP 429  Insufficient budget. This request has no API key, so it counts
          against the free daily budget shared by everyone on your network's IP
```

所以本项目**没有把 OpenAlex 当主干**。额度用尽会自动熔断，其余数据源照常工作。
想彻底解决，去 <https://openalex.org> 申请一个免费 Key：

```powershell
$env:OPENALEX_API_KEY = "你的key"          # 或写进 config.toml 的 [sources]
python -m priceradar run
```

本项目对 OpenAlex 的用法很省：**只对缺摘要的文章、按 DOI 每 50 篇一次批量查询**，
预热好的话一天 1–3 次请求就够。

### 摘要覆盖率说明

价格研究里最关键的判断依据是摘要。实测在最近 14 天窗口内：

- **Wiley / OUP / INFORMS / AEA**（JF、RFS、QJE、Management Science、AER、AJAE）→ Crossref 直接给摘要，**覆盖率接近 100%**
- **Elsevier**（Energy Economics、JEEM、J. Commodity Markets、J. Econometrics、IJF、Food Policy）→ Crossref **不给摘要也不给在线日期**，ScienceDirect 有反爬抓不了

对策（按性价比排序）：

1. **配 OpenAlex Key**（最有效，Elsevier 摘要基本补齐）
2. 依赖标题打分 —— 这个场景其实够用：`oil price`、`futures`、`carbon price` 这类词几乎一定出现在标题里
3. 日报里对无摘要的文章加了显式提示 `⚠ 该刊未提供摘要，本条基于标题判相关性`，不会让你误判

---

## 5. 打分规则（完全可解释）

```
相关性 = 3.0 × 价格词命中(标题) + 0.8 × 价格词命中(摘要)
       + 2.5 × 商品期货词命中(标题) + 0.6 × 商品期货词命中(摘要)

综合分 = 100 × ( 0.50 × 相关性(封顶14) + 0.20 × 期刊权重
              + 0.15 × 时效 + 0.10 × 方法匹配 + 0.05 × 有摘要 )
       + 1.5 × 有免费全文
```

- **价格词**（`core`）：price / prices / pricing / markup / inflation / price discovery / convenience yield / yield / exchange rate …
- **商品期货词**（`context`）：commodity / futures / crude / WTI / Brent / natural gas / electricity / carbon / wheat / copper / hedging / basis / contango / OPEC …
- **方法词**（`method`）：GARCH / cointegration / forecasting / VAR / high-frequency / event study / DSIM …（只加分，不筛除）
- **排除词**（`exclude`）：prize / erratum / corrigendum / book review / call for papers …（标题命中直接丢弃）

匹配细节：忽略大小写；`pass-through` 与 `pass through` 等价；自动容忍词尾复数（`price` 匹配 `prices`）；
使用自定义词边界避免 `rapid` 命中 `price` 之类的误伤。

**门槛与兜底**：优先取「标题含价格词」的文章，并限制每刊最多 3 篇以保证来源多样性；
如果严格池凑不满 10 篇，依次放宽为「取消每刊限额」→「摘要含价格词也算」→「有什么推什么」。
每一步都会打印在日志里，你随时知道今天的 10 篇是严格命中还是放宽来的。

---

## 6. 三种定时运行方式

### 方式 A：Windows 计划任务（推荐，本机）

```powershell
# 先手动跑一次确认没问题
.\run_daily.ps1 -Open

# 注册每天 08:30 自动运行
schtasks /create /tn "PriceRadar 每日推送" `
  /tr "powershell -NoProfile -ExecutionPolicy Bypass -File $PWD\run_daily.ps1" `
  /sc daily /st 08:30

# 想删除
schtasks /delete /tn "PriceRadar 每日推送" /f
```

日志写在 `data/logs/run-YYYY-MM-DD.log`。电脑关机/休眠时当天不会跑，第二天正常。

### 方式 B：GitHub Actions（免费、云端、不占本机）

见上面 **第 2 节 · 方式 2**，那套步骤同时也是「每天自动更新公网看板」的做法。
要点回顾：加 `PRICERADAR_MAILTO` Secret → Pages Source 选 GitHub Actions →
加 `ENABLE_PAGES=true` 变量。默认 `00:30 UTC`（北京 08:30）自动运行。

> 注意：GitHub Actions 的 cron 在高峰期可能延迟几分钟到几十分钟；私有仓库的
> Actions 时长会消耗免费额度（本任务每天约 1–2 分钟，完全够用）。

### 方式 C：自己的服务器 / 树莓派

```bash
chmod +x run_daily.sh
crontab -e
# 加入：30 8 * * * cd /path/to/price-radar && ./run_daily.sh >> data/logs/cron.log 2>&1
```

服务器上想让同事访问，用内置的 serve（会打印局域网 IP）：

```bash
python -m priceradar serve --port 8080
# 想暴露到公网：前面挂 nginx / caddy 反代，或用 Cloudflare Tunnel
```

---

## 7. 配置速查（`config.toml`）

| 配置项 | 默认 | 说明 |
| --- | --- | --- |
| `digest_size` | 10 | 每天推几篇 |
| `lookback_days` | 14 | 回溯窗口。想更「新」就调小到 7，想不漏就调到 21 |
| `max_per_journal` | 3 | 单刊上限，保证来源多样性 |
| `mailto` | 见文件 | 你的真实邮箱。Unpaywall 会拒绝 `example.com` |
| `public_url` | 空 | 你的公网地址（如 `https://xx.github.io/price-radar`），RSS 自引用用 |
| `[keywords] core/context/method/exclude` | 见文件 | 你最需要反复微调的地方 |
| `[sources] openalex_api_key` | 空 | 或环境变量 `OPENALEX_API_KEY` |
| `sources.enrich_missing_abstract` | true | 关掉可省额度，但摘要覆盖率会下降 |
| `sources.unpaywall_max` | 40 | 只为前 N 篇查免费全文 |
| `sources.s2_interval` | 3.5 | Semantic Scholar 未配 Key 时容易被限流，别调小 |

调完想重新渲染历史日报（不用重新抓取）：

```powershell
python -m priceradar rebuild
```

---

## 8. 命令速查

```powershell
python -m priceradar resolve           # 期刊名 → ISSN（首次必跑）
python -m priceradar resolve --refresh # 强制重新解析（换期刊后）
python -m priceradar doctor            # 体检：数据源、期刊解析、试抓取
python -m priceradar doctor --fetch 5  # 顺带试抓前 5 本刊
python -m priceradar run               # 生成今天的日报
python -m priceradar run --open        # 生成并打开看板
python -m priceradar run --limit 15    # 今天推 15 篇
python -m priceradar run --dry-run     # 只看结果，不写库不出文件（调试用）
python -m priceradar run --force       # 当天已生成过也重新生成（会覆盖当天日报）
python -m priceradar run --no-dedup    # 忽略历史去重，允许重复推送已推过的文章
python -m priceradar run --no-enrich   # 跳过摘要/OA 补充（省额度、省时间）
python -m priceradar run --candidates data/cand.json  # 顺便把候选池存下来，便于离线调规则
python -m priceradar run --no-fetch --candidates data/cand.json  # 用候选池离线跑（调关键词神器）
python -m priceradar run --email       # 生成后发邮件（需 SMTP 环境变量）
python -m priceradar serve             # 局域网分享看板（打印同事要用的地址）
python -m priceradar stats             # 看历史推送记录
python -m priceradar rebuild           # 用存档 JSON 重新渲染 HTML 和 RSS
```

> **一天只出一期**：如果 `<日期>.json` 已经存在，重复运行会直接跳过并提示
> `已存在（10 篇），跳过`。这是防止定时任务重跑或手动重跑把当天日报覆盖掉。
> 确实要重跑就加 `--force`。

去重策略有个细节值得知道：**只有真正推送过的文章才会被永久排除**。
当天没挤进前 10 的候选，明天还会继续参与竞争 —— 所以好文章不会因为一次排名第 11 就永远看不到。

**调关键词的正确姿势**：先 `--candidates` 存一份候选池，然后反复改 `[keywords]` 配
`--no-fetch --candidates ... --dry-run`，几秒钟一轮，不用重复打网络请求。

---

## 9. 邮件推送（可选）

```powershell
$env:PRICERADAR_SMTP_HOST = "smtp.qq.com"
$env:PRICERADAR_SMTP_PORT = "465"
$env:PRICERADAR_SMTP_USER = "you@qq.com"
$env:PRICERADAR_SMTP_PASS = "授权码"        # 注意是授权码，不是登录密码
$env:PRICERADAR_MAIL_TO   = "you@qq.com,a@b.com"   # 多个收件人用逗号分隔
python -m priceradar run --email
```

邮件是 HTML 格式，和看板一样可点。没配置时只打印一行提示，不影响日报生成。
想发给同事，直接把邮箱加进 `PRICERADAR_MAIL_TO` 就行 —— 这是最不需要对方配合的分发方式。

---

## 10. 想再加推送渠道？

推送逻辑和渲染是解耦的，加一个渠道只需要三步：

1. 在 `priceradar/` 下新建 `feishu.py`（或钉钉/企业微信/Server酱），
   入参就是 `digest` 字典（`digest["items"]` 是那 10 篇文章，字段见 `data/out/*.json`）；
2. 参照 `mailer.py` 的写法，用 `urllib.request` POST 一个 Webhook；
3. 在 `__main__.py` 的 `cmd_run` 里加一个 `--feishu` 分支。

想加**中文标题/摘要翻译**？同样是一个独立适配器：遍历 `digest["items"]`，
调你惯用的翻译或大模型 API 覆盖 `item["title_zh"]` / `item["abstract_zh"]`，
再在 `render.py` 里优先显示 `_zh` 字段即可。刻意没有内置，是为了不引入 Key 依赖和失败路径。

---

## 11. 文件结构

```
price-radar/
├── config.toml                  # 唯一需要改的文件：期刊、关键词、数据源、public_url
├── index.html                   # 根跳转页（分支模式 GitHub Pages 用）
├── run_daily.ps1 / run_daily.sh # 一键生成日报
├── share.ps1                    # 一键局域网分享（自动放行防火墙）
├── .nojekyll                    # 让 GitHub Pages 跳过 Jekyll
├── .github/workflows/daily.yml  # GitHub Actions 云端定时 + 可选 Pages 发布
├── priceradar/
│   ├── __main__.py              # 命令行入口
│   ├── config.py                # 配置加载 + 默认关键词
│   ├── http.py                  # 标准库 HTTP：重试/退避/限流/额度熔断
│   ├── sources.py               # Crossref / RSS / S2 / Unpaywall / OpenAlex
│   ├── score.py                 # 可解释打分与筛选门槛
│   ├── store.py                 # SQLite 去重（不重复推送）
│   ├── render.py                # Markdown + HTML 看板 + RSS
│   ├── server.py                # 局域网分享服务器
│   ├── mailer.py                # 可选邮件推送
│   └── pipeline.py              # 主流程编排
└── data/
    ├── sources_cache.json       # 期刊解析结果（自动生成）
    ├── priceradar.sqlite3       # 推送历史（去重依据）
    ├── logs/                    # 运行日志
    └── out/                     # 日报产物：index.html 是最新一期，feed.xml 是订阅源
```

---

## 12. 成本

**0 元**。不需要任何付费 Key、不需要服务器（跑本机计划任务、或 GitHub Pages /
Cloudflare Pages 的免费额度）。唯一可选的是申请 OpenAlex 免费 Key 来提高摘要覆盖率 ——
那也还是免费。

---

## 13. 已知限制（诚实清单）

1. **默认只有你自己能看** —— 必须用第 2 节的任一方式给出网址，别直接发本地路径。
2. **局域网方式要求你的电脑开着** 且和对方在同一网络；IP 会在路由器重启后变化。
3. **Elsevier 系期刊的摘要拿不到**（第 4 节详述）—— 配 OpenAlex Key 可基本解决。
4. **Econometrica 这类刊窗口内经常是 0 篇** —— 它们本来出刊就慢，不是抓取失败。
5. **GitHub Actions 的 cron 不精确** —— 高峰期可能延迟几十分钟。
6. **星期天大概率没有新文章** —— 顶刊很少周末更新，当天日报可能不足 10 篇，这是正常的。
7. **Semantic Scholar 未配 Key 时会限流** —— 已做指数退避 + 单批次熔断，不会拖垮整个流程。
8. **期刊匹配依赖名称相似度** —— `resolve` 会对「规模过小」的匹配打印 ⚠ 警告
   （比如 `Journal of Commodity Markets` 只有 405 篇 DOI 是正常的，它 2016 年才创刊）。
   如果匹配错了，在 `config.toml` 里直接写 `issn = ["0022-1082"]` 钉死即可。
9. **serve 没有访问控制** —— 局域网内谁都能看。要限制就用 Cloudflare Pages + Access，
   或者只在自己机器上用 `--local`。
