# Desktop agent hosts

This skill supplies editing procedures and Python scripts, not desktop-control permissions. Use the host's own authorized Windows shell and desktop tools. Do not invent a remote tool name or require Remote Desktop Commander when the host already executes locally.

## Desktop Doubao / 桌面豆包

- 在“本地电脑”任务环境执行。云电脑中的 Linux Python 不能调用 Windows 剪映 DLL。
- 使用已安装的 `jianying-editor-115`；从本次技能加载信息确定根目录，检查 `scripts/modern_draft.py` 存在。不要继续调用旧 `jianying-editor` 写入 11.x 草稿。
- 检查本机 64 位 Python 和实际剪映版本，设置 `JY_INSTALL_DIR`。加密读写、复制编辑无需 pip 安装额外包。
- 首次只读检查已知草稿并报告选中的主时间线、编码、时长、轨道数。读文件不需要退出剪映；写副本前正常退出。
- 编辑现有项目严格执行主 SKILL.md 的副本流程。若任务环境只能读取上传文件、不能执行本机 Windows 命令，明确报告缺少本机执行能力，不得宣称安装后即可操作剪映。
- 旧技能可继续保留用于其他场景。用户明确请求 11.5 加密草稿操作时优先采用本技能；不要私自删除其他技能。

## Local Codex

Resolve this skill from the installed skill list or the user-provided folder. If the task runs in WSL, execute the native codec with an observed Windows x64 Python executable and Windows paths, not WSL Python. Preserve the host's approval settings. Read-only inspection and a successful codec roundtrip do not establish visual editing/export success.

## First-use prompt

“使用 jianying-editor-115，在本地 Windows 检查剪映版本、videoeditor.dll 路径和指定草稿的编码。先只读检查，不修改草稿。后续所有编辑另建副本，保留原工程。”

Use new-projects.md only when a prepared full runtime is available. This lightweight skill does not bundle the old effect catalogs or claim unattended 11.5 export.
