# Jianying Editor 11.5

**Windows 剪映 11.5 加密草稿兼容扩展 · Agent Skill · v0.1.1**

让具备本机执行能力的 AI 助手读取剪映加密草稿，在独立副本中修改字幕、音量等数据，并重新加密保存。实测版本：**剪映专业版 11.5.0.14471 / Windows x64**。

An independent Agent Skill for inspecting and editing encrypted Jianying drafts through the user's installed Windows DLL, with source-preserving copy edits and roundtrip verification.

这是独立的社区兼容扩展，基于 [luoluoluo22/jianying-editor-skill](https://github.com/luoluoluo22/jianying-editor-skill) v1.7.0 的工作流，并参考 [wenshui330/jy-draftc](https://github.com/wenshui330/jy-draftc) 的本机 DLL 调用方式。不是剪映、豆包或 OpenAI 的官方项目，也不代表上游作者发布了 11.5 支持。

## v0.1.1 修复

保留调用方提供的工程根目录写法，修复 Windows 8.3 短路径别名在复制工程时未同步迁移内部素材路径的问题。输出路径仍使用规范路径，测试同时按规范路径校验。建议使用 v0.1.1 或更高版本。

## 可以做什么

| 能力 | 状态 |
| --- | --- |
| 识别明文 JSON、Base64 JSON 和加密候选格式 | 已验证 |
| 使用本机 `videoeditor.dll` 解密、重新加密并检查往返一致性 | 11.5.0.14471 实测通过 |
| 选择主时间线，避免误读旧 `draft_info.json` | 已验证 |
| 在新副本中替换已有字段，保留未知字段、媒体和文件编码 | 已验证 |
| 修改文本数据后在剪映保存、完全退出、重开并回读 | 实测通过；不等于所有字幕样式均已视觉验收 |
| 通过可选完整运行目录生成新项目 | 继承旧版 API；需在目标剪映中验收 |
| 多个有效时间线一起编辑 | 当前拒绝执行 |
| macOS / Linux 本机解密 | 不支持；加密操作需要 Windows x64 |
| 一键无人值守导出、所有特效、其他剪映版本 | 尚未验证或适配 |

**安装 Skill 不会让一个只有聊天能力的客户端自动获得操作电脑的权限。** AI 助手必须能够执行用户本机 Windows 命令；界面验收还需要桌面操作能力。

## 获取与安装

发布包分为两种：

- `jianying-editor-115-v0.1.1.zip`：标准技能包，解压后单个顶层目录中包含 `SKILL.md`、`scripts/` 和 `references/`。
- `jianying-editor-115-github-v0.1.1.zip`：完整仓库源码，含中文说明、许可、测试和打包脚本。用于建立 GitHub 仓库；不要把它当成仅含技能的导入包。

### 桌面豆包

在支持自定义技能的豆包工作中，通过技能管理页面导入标准技能 ZIP。使用时选择**本地电脑**环境，并明确指定 `jianying-editor-115`。旧 `Jianying Editor` 可以保留；编辑 11.5 加密草稿时使用本扩展。

首次发给豆包：

```text
使用 jianying-editor-115，在本地 Windows 检查剪映版本、videoeditor.dll 的实际路径和我指定草稿的编码。先只读检查，不修改草稿。确认使用当前技能的 scripts/modern_draft.py；后续修改一律另建副本。不要用旧 JyProject 序列化器重写 11.5 原工程，不要宣称已完成自动导出。
```

如果客户端没有导入入口，或技能运行在无法访问本机的云环境，先解决宿主能力问题。不要把 Windows DLL 上传到云电脑。

### 本地 Codex

把 `skills/jianying-editor-115` 文件夹安装到 Codex 的用户或项目技能目录，例如用户级 `~/.agents/skills/jianying-editor-115`，然后在技能列表中选择它。也可直接让 Codex 读取该文件夹的 `SKILL.md`。若 Codex 运行在 WSL，加密操作仍须调用 Windows x64 Python。

### 其他 Agent

使用支持 `SKILL.md` 的本地 Agent。完整导入文件夹，不要只粘贴提示词：脚本、许可和参考文件都属于技能。是否能直接控制剪映界面取决于宿主工具，不能仅凭导入成功推断。

## 环境要求

- Windows x64、64 位 Python；建议 Python 3.12 或更高。原始本机验证使用 Python 3.14。
- 用户自己安装的剪映专业版。将 `JY_INSTALL_DIR` 设置为包含 `videoeditor.dll` 的**版本目录**。
- 核心加密读写和副本编辑只用 Python 标准库，无需安装额外 pip 包。
- 写副本前正常退出剪映。只读检查不要求退出。

不附带剪映 DLL、密钥、安装器、私有工程或素材。代码不会修改剪映二进制，也不包含付费素材解锁功能。

## 手动检查草稿

以下路径均为占位示例，需要替换成当前电脑上实际存在的路径：

```powershell
$skillRoot = 'C:\Tools\jianying-editor-115'
$env:JY_INSTALL_DIR = 'C:\Path\To\JianyingPro\11.5.0.14471'
python "$skillRoot\scripts\modern_draft.py" inspect 'D:\Drafts\Source'
```

`inspect` 返回当前主时间线的 `selected_file`、`source_sha256`、编码和概要。不要猜测主时间线文件的位置。

如需编辑：先用 `decode` 将 **selected_file** 解码到一个不存在的新文件，依据实际字段构造补丁；补丁必须带本次检查的哈希和旧值：

```json
{"source_sha256":"<inspect 返回的实际哈希>","operations":[{"op":"replace","path":"/tracks/0/segments/0/volume","expected":1.0,"value":0.8}]}
```

上例只有在目标片段确实存在且旧音量为 `1.0` 时才成立。字幕正文常是嵌套 JSON 字符串；修改文字时必须同时处理样式范围。JSON 结构验证无法代替剪映中的画面和声音验收。

```powershell
python "$skillRoot\scripts\modern_draft.py" decode '<selected_file>' 'D:\Work\source-readonly.json'
python "$skillRoot\scripts\modern_draft.py" clone 'D:\Drafts\Source' 'D:\Drafts\Review-Copy' --patch 'D:\Work\patch.json'
```

目的目录必须不存在，且不能位于原工程内部。工具检查源文件哈希、同步主时间线镜像、保留编码并生成新的工程元数据；不会自动把副本登记进剪映的草稿目录。`native_ui_verified=false` 表示仍需在剪映中打开、检查、保存和重开，不能当成成片完成。

## 可选：旧版新建工程 API

核心包已足够检查和修改现有加密工程。只有需要旧版 `JyProject` API、素材目录和规则时才准备完整运行目录：

```powershell
git clone https://github.com/luoluoluo22/jianying-editor-skill.git upstream-jianying
git -C upstream-jianying checkout 32c56928ded4f9e2c2b80e099dc7abb793d2c30b
python skills/jianying-editor-115/scripts/prepare_runtime.py --source upstream-jianying --destination jianying-full-runtime
```

该命令应用固定版本补丁，保留上游许可，拒绝覆盖已有目标。旧 API 只用于尚未被剪映保存过的新项目；剪映保存后的加密、多文件工程必须改用现代副本编辑器。额外功能依赖按需要安装在独立虚拟环境中。

## 测试

从仓库根目录运行：

```powershell
python -m unittest discover -s skills/jianying-editor-115/scripts -p 'test_*.py' -v
```

轻量包运行 12 项核心测试，另 2 项依赖完整运行目录的测试会明确跳过。准备完整运行目录后：

```powershell
$env:JY_LEGACY_TEST_RUNTIME = (Resolve-Path '.\jianying-full-runtime').Path
python -m unittest discover -s skills/jianying-editor-115/scripts -p 'test_*.py' -v
```

全部 14 项已通过。自动测试使用合成工程，不要求上传私人草稿；它们不证明 DLL 在其他安装版本上可用。

本机实测记录：2026-09-30，剪映 11.5.0.14471，成功读取真实加密工程，编辑副本、重新加密、在原生编辑器打开和播放、保存、完全退出后冷启动重开，修改的文本数据保留，原工程全部文件哈希未变。

## 在 GitHub 发布

建议仓库名：`jianying-editor-115`。将源码包解压后的仓库内容上传到你自己的仓库；不要把整个 ZIP 当作唯一源码文件上传。创建 `v0.1.1` Release，并附上标准技能 ZIP 和 `SHA256SUMS.txt`。

从源码重新构建发布包：

```powershell
python tools/build_release.py
```

产物在 `dist/`。公开前确认仓库只含代码、文档、许可和合成测试，不包含草稿、DLL、录屏、凭据和个人绝对路径。

## 许可与致谢

本扩展以 MIT 许可发布，见 [LICENSE](LICENSE)。衍生部分保留原许可，见 [NOTICE.md](NOTICE.md)。可选完整运行目录中的 `pyJianYingDraft` 适用 Apache-2.0。

欢迎提交其他剪映版本的兼容性结果。报告问题请提供版本号、Python 位数、脱敏错误和可复现的合成样例；不要提交私人草稿或剪映 DLL。
