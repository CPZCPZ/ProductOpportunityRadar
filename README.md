# 产品机会雷达 (Product Opportunity Radar)

一个零运维、零成本的自动化工具：每天定时从**海外 + 国内**多个**官方 API / 官方 RSS** 信源抓取「有人在求工具 / 痛点 / 新品 / 趋势」的信号，经去重和机会打分排序后，渲染成一封手机友好的 HTML 日报邮件发送到你的邮箱，作为一人公司选品的参考。

每条机会都标注**来源平台 + 原帖直达链接 + 推广渠道提示**，方便溯源和（新手）推广。

---

## 它能做什么

```
官方信源采集 → 统一信号模型 → 去重 → 机会打分(热度+痛点关键词+时效) → 排序 → 渲染 HTML 日报 → SMTP 邮件
```

- 海外：Hacker News（Algolia 官方 Search API）、Reddit（官方 OAuth API）、Product Hunt（官方 GraphQL，可选）、Indie Hackers 等官方 RSS
- 国内：V2EX（官方 API）、App Store 中国区（Apple 官方 iTunes RSS）、少数派 / 36氪（官方 RSS）

> 合规说明：本工具只消费各平台**主动公开发布**的 API / RSS，遵守频率限制与 User-Agent 规范；不抓取登录后内容、不绕过反爬、不采集个人数据。

---

## 快速开始（本地）

1. 安装依赖（建议 Python 3.11+）：

```bash
pip install -r requirements.txt
```

2. 复制配置并填写：

```bash
cp .env.example .env
```

至少填好 `SMTP_*` 和 `MAIL_TO` 即可跑通（Reddit / Product Hunt 不配会自动跳过）。

3. 运行：

```bash
python -m src.main
```

跑通后你的邮箱会收到一封日报。也可以加 `--dry-run` 只在本地生成 HTML 不发邮件：

```bash
python -m src.main --dry-run
```

`--dry-run` 会把日报写到 `output/radar-YYYY-MM-DD.html`，用浏览器打开预览即可。

---

## 邮箱 SMTP 配置示例

| 邮箱 | SMTP_HOST | SMTP_PORT | SMTP_PASS |
|------|-----------|-----------|-----------|
| QQ邮箱 | smtp.qq.com | 465 | 授权码（设置→账户里开启并生成，**不是登录密码**） |
| 163邮箱 | smtp.163.com | 465 | 授权码 |
| Gmail | smtp.gmail.com | 465 | 应用专用密码 |

> 手机查看：HTML 邮件是邮件标准格式，所有手机邮件客户端点开即自动排版，无需下载文件。若想长期归档，可在 `.env` 设 `ATTACH_FILE=true`，邮件会额外带一个日报文件附件。

---

## 申请 API 凭据（可选，但推荐配 Reddit）

- **Reddit**（强烈推荐）：访问 https://www.reddit.com/prefs/apps → 创建 `script` 类型应用 → 把 client id / secret 填入 `.env`。不配则跳过 Reddit。
- **Product Hunt**（可选）：https://www.producthunt.com/v2/oauth/applications → 创建应用拿 Developer Token。不配则跳过。

---

## 部署到 GitHub Actions（免费、每日自动发送）

1. 把本项目推到一个 GitHub 仓库（公开/私有都行，私有每月有 2000 分钟免费额度，足够）。
2. 仓库 `Settings → Secrets and variables → Actions → New repository secret`，添加：
   - `SMTP_HOST` `SMTP_PORT` `SMTP_USER` `SMTP_PASS` `MAIL_TO`
   - 可选：`REDDIT_CLIENT_ID` `REDDIT_CLIENT_SECRET` `REDDIT_USER_AGENT` `PRODUCTHUNT_TOKEN` `ATTACH_FILE`
3. 工作流 `.github/workflows/daily-radar.yml` 已配好定时（默认每天北京时间 09:00）。修改里面的 `cron` 可调整时间（注意 cron 用 UTC）。
4. 进 `Actions` 页可手动点 `Run workflow` 立即测试一次。

> 注意：GitHub 规定**仓库连续 60 天无提交活动会自动暂停定时任务**。偶尔提交一次（或让日报本身提交一个 run 记录）即可保持激活。

---

## 调整信源 / 阈值

不用改代码，编辑这两个文件即可：

- `sources.yml`：开关各信源、subreddit 列表、RSS 地址、抓取条数、`top_n_*`、`recent_hours` 等。
- `keywords.yml`：中英文痛点关键词库，命中即加权。
- `promotion.yml`：来源 → 推广渠道映射（决定每条机会下方"推广提示"显示什么）。

---

## 一人公司可做的工具方向（赠送清单）

拿本雷达验证下面这些方向的真实需求，再动手：

1. **细分行业 SaaS**：给某个小众职业/行业做的轻量管理或自动化工具（垂直越窄越好）。
2. **浏览器插件**：解决某个网站使用痛点（数据导出、批量操作、界面增强）。
3. **API 封装小工具**：把复杂 API（地图、AI、支付、数据）封装成傻瓜式产品或订阅。
4. **自动化脚本订阅**：像本项目一样，"定时抓取+整理+推送"类信息差工具。
5. **文档/格式转换**：PDF、图片、表格、字幕等格式互转与批处理。
6. **内容/素材生成器**：模板化生成简历、海报、合同、周报等。
7. **数据监控告警**：价格/库存/排名/关键词监控并通知。

**如何用日报验证**：当某个痛点关键词反复在不同来源出现、且帖子有真实互动（评论/点赞）时，说明需求真实且高频——优先做这种。每条机会下方的"推广提示"会告诉你目标人群在哪、第一步该怎么冷启动。

---

## 目录结构

```
ProductOpportunityRadar/
├── .github/workflows/daily-radar.yml
├── src/
│   ├── main.py            # 编排入口
│   ├── config.py          # 读取 env / yml
│   ├── models.py          # Signal 数据模型
│   ├── scoring.py         # 机会打分
│   ├── dedupe.py          # 去重
│   ├── render.py          # Jinja2 渲染 HTML
│   ├── mailer.py          # SMTP 发送
│   └── collectors/        # 各信源采集器（仅官方 API/RSS）
├── templates/email.html.j2
├── keywords.yml
├── promotion.yml
├── sources.yml
├── requirements.txt
├── .env.example
└── README.md
```
