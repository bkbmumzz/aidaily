# 🔥 aidaily - GitHub 每日热门开源项目日报

每日自动抓取 GitHub 热门开源项目，生成 Markdown 报告和静态网站。

## 数据维度

| 维度 | 说明 |
|------|------|
| 🔥 Trending 总榜 + 语言分类 | 按日/周/月抓取 GitHub Trending 页面 |
| 🚀 Star 增长最快 | 过去 7 天内活跃且 star 最高的项目 |
| 🆕 新创建的高星项目 | 最近 30 天创建且 star > 100 的项目 |
| 💬 热门 Issue/PR | 近期评论数最高的 Issue 和 PR |

## 快速开始

```bash
# 1. 安装依赖
pip install -e .

# 2. 设置 GitHub Token (可选，不设置则只抓取 Trending)
export GITHUB_TOKEN=your_github_token

# 3. 运行 (仅 Trending 模式，无需 Token)
python -m src.main --trending-only

# 4. 运行 (完整模式，需要 Token)
python -m src.main
```

## 输出

- `data/reports/YYYY-MM-DD.md` - Markdown 每日报告
- `data/json/YYYY-MM-DD.json` - 结构化 JSON 数据
- `docs/index.html` - 静态网站首页

## GitHub Token

获取地址: https://github.com/settings/tokens

只需要 `public_repo` 权限即可。未设置 Token 时，仅抓取 Trending 数据（不需要 API 调用）。

## 项目结构

```
├── config/          # 配置
├── src/
│   ├── fetcher/     # 数据抓取 (Trending + GitHub API)
│   ├── processor/   # 数据处理 (模型 + 去重 + 存储)
│   ├── reporter/    # Markdown 报告生成
│   └── site/        # 静态网站生成
├── data/            # 运行时数据
├── docs/            # 静态网站输出
└── tests/           # 测试
```

## License

MIT
