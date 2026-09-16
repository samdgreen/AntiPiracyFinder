# AntiPiracy Reporter v0.1.1-slim

精简发布版。主要变化：完全移除 pandas / numpy，Excel 读取和报告生成改用 openpyxl，以显著降低 PyInstaller EXE 体积。

## 支持输入
- `.xlsx`
- `.txt`

旧式 `.xls` 不再内置支持。请用 Excel/WPS 另存为 `.xlsx` 后导入。

## Windows 打包
双击 `build_exe.bat`。完成后真正的程序是：

`dist\AntiPiracyReporter.exe`

不要使用或上传 `build/` 中的 `.toc` 等 PyInstaller 中间文件。

## 功能保持
- GUI 上传上一个工具导出的链接
- 服务商/CDN/注册商/IP 分析
- 自动生成 Excel 报告
- 复制中/英文申诉文本
- 打开对应官方举报入口
- 关闭应用前确认

报告默认保存到 `Documents\AntiPiracyReporter_Results`。


## v0.1.2 打包修复

如果旧版 `build_exe.bat` 出现 `'itle'`、`'tall'`、`'mdir'` 等“不是内部或外部命令”，这是 Windows CMD 对批处理文件编码/换行解析异常。

v0.1.2 的 `build_exe.bat` 已改为：
- 纯 ASCII 内容
- Windows CRLF 换行
- 不再使用 `chcp`
- 不再在 BAT 中写中文
- PyInstaller 命令改为单行，避免 `^` 续行解析问题

请删除旧的 `build/`、`dist/` 后直接双击新版 `build_exe.bat`。


## v0.1.3 文件导入修复

现在点击“打开 / 上传”并选择 `.xlsx` 或 `.txt` 后，程序会**立即读取文件**，而不是只把文件路径放进输入框。

成功后会显示：
- `已导入 N 条链接`
- 弹窗提示实际识别到的链接数量

如果文件里没有识别到 HTTP/HTTPS 链接，会立即提示，不会等到“开始识别运营商”后才发现。


## v0.1.4 Path 修复

修复选择文件后出现 `name 'Path' is not defined` 的问题。
文件导入界面使用 `pathlib.Path` 显示文件名、检查文件是否存在和创建报告目录，
本版本已在 `app.py` 顶部显式加入 `from pathlib import Path`。
