# Iconfont → ICO 转换器

将 [iconfont.cn](https://www.iconfont.cn/) 导出的 SVG 符号（`iconfont.js` + `iconfont.json`）批量转换为 **Windows 多尺寸 `.ico`**，可直接用于 PyInstaller：

```bash
pyinstaller --onefile --icon=output_icons/app.ico your_script.py
```

## 环境要求

- Python 3.10+
- Windows（也可在其他系统运行，本工具面向 Windows `.ico`）

## 安装

```bash
pip install -r requirements.txt
```

## 运行 GUI

在项目根目录执行：

```bash
python -m src
```

默认输入目录：`ai_icon/font_6xww5b6c7bv`  
默认输出目录：`output_icons/`

## 使用说明

1. **输入目录**：需包含 `iconfont.js` 与 `iconfont.json`（iconfont 项目「下载至本地」的 Symbol 方式）。
2. **输出目录**：批量生成的 `{font_class}.ico` 保存位置。
3. **图标列表**：单击行可勾选/取消；支持全选、全不选、反选。
4. **预览**：选中图标后在右侧查看 256px 预览。
5. **背景**：白底（推荐，exe 图标显示更稳定）或透明。
6. **ICO 尺寸**：建议全选 16 / 32 / 48 / 256，以满足资源管理器与 PyInstaller 需求。
7. 点击 **批量导出 .ico**。

## 项目结构

```
src/
  icon_extractor.py   # 解析 iconfont.js / json，组装独立 SVG
  ico_builder.py        # PyMuPDF 栅格化 + Pillow 合成 ICO
  gui.py                # Tkinter 图形界面
  __main__.py           # python -m src 入口
ai_icon/                # 示例 iconfont 资源
requirements.txt
```

## 技术说明

- 矢量来源：`iconfont.js` 内 `window._iconfont_svg_string_` 中的 `<symbol>` 节点。
- 栅格化：PyMuPDF (`fitz`) 将 SVG 渲染为位图。
- ICO：Pillow 将多尺寸 PNG 写入单个 `.ico` 文件。

## 打包为可执行程序

```bash
pip install pyinstaller
pyinstaller IconfontToIco.spec
```

生成 `dist/IconfontToIco.exe`，程序图标为 `output_icons/draw.ico`，内置示例 `ai_icon/`，导出默认写到 exe 同目录下的 `output_icons/`。
