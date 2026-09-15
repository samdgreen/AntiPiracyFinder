# AntiPiracy Finder

**当前版本：v0.1.0-beta**

AntiPiracy Finder 是一个面向网络文学作者的免费开源辅助工具，用于整理搜索引擎公开展示的、可能与盗文/转载有关的链接，方便作者后续人工核实、保存线索和进行投诉。

> 本工具只负责记录搜索引擎公开展示的链接，不会自动访问或验证候选网站。

## 功能

- Windows 图形界面，普通用户可直接运行发布版 EXE
- 使用 Microsoft Edge
- 支持当前 Edge 中的 Google、Bing、百度、Quark 搜索结果
- 自适应导航：数字页码 → “下一页”/箭头 → 无限滚动
- 每次导航后确认页面确实发生变化，再继续采集
- 自动去重
- 最终导出前排除明显的“晋江文学城 / jjwxc”正版结果
- 自动导出 Excel，仅保留：`标题 / 网址 / 来源`
- 每次导出使用搜索引擎和时间戳命名，避免覆盖旧结果

## 普通作者如何使用

1. 从 GitHub **Releases** 下载 `AntiPiracyFinder.exe`。
2. 双击运行。
3. 输入书名和作者名。
4. 点击 **启动 / 连接 Edge**。
5. 在程序启动的专用 Edge 中，手动使用 Google、Bing、百度或 Quark 搜索作品。
6. 保持搜索结果页为当前页面，回到程序点击 **采集当前搜索并自动导出 Excel**。
7. Excel 会保存到：

   `文档\AntiPiracyFinder_Results`

搜索引擎的页面结构可能因地区、账号、时间或版本而不同。本项目采用多种翻页方式逐级 fallback，但搜索引擎改版仍可能导致部分页面暂时无法自动采集。

## 关于 403 和候选链接

本工具**不会自动打开候选网站，也不会尝试绕过 403、验证码或其他访问限制**。

导出的链接可能：
- 返回 403；
- 要求验证码；
- 已失效；
- 与作品无关；
- 并不构成侵权。

请作者自行打开并核实，再决定是否投诉或保存证据。

## 从源码运行

需要 Python 3 和 Microsoft Edge。

```bat
python -m pip install -r requirements.txt
python app.py
```

## 在 Windows 上构建 EXE

双击：

```text
build_exe.bat
```

成功后文件位于：

```text
dist\AntiPiracyFinder.exe
```

构建脚本已经显式收集 Selenium 的 Edge WebDriver 相关模块。

## GitHub 自动构建

仓库包含 `.github/workflows/build-windows.yml`。

- 手动运行 workflow：生成 Windows EXE artifact。
- 推送形如 `v0.1.0-beta` 的 tag：自动构建并创建 GitHub Release，附加 `AntiPiracyFinder.exe`。

## 项目定位

这是一个免费的作者反盗文辅助工具，不收费。欢迎提交 Issue、Pull Request 或代码优化。

## License

MIT License。
