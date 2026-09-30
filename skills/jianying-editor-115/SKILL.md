---
name: jianying-editor-115
description: Operate Windows Jianying Pro, including 11.5 encrypted drafts, through local native decoding, verified re-encryption, guarded project-copy editing and desktop UI verification. Use for 剪映自动剪辑、加密草稿、draft_content.json、修改字幕/音量/时间线、11.5兼容、更新jianying-editor-skill. Provides a pinned upstream compatibility patch for new-project generation; route app-saved projects through the modern copy editor. Requires access to the user's Windows machine and installed Jianying DLL for encrypted files.
---

# 剪映 11.5 编辑助手

Treat this as an independent compatibility extension of `luoluoluo22/jianying-editor-skill` v1.7.0. Execute scripts on the user's Windows machine through the host's local shell or connected Windows tools; cloud Linux cannot load the Windows DLL. Each agent host needs its own installation. For desktop Doubao and local Codex, read [desktop-hosts.md](references/desktop-hosts.md).

Read [compatibility.md](references/compatibility.md) for verified capabilities and limits. Preserve source license notices. Do not distribute Jianying's DLL or upload private drafts to a decryption service.

## Route the operation

1. Inspect app-saved/encrypted projects with `scripts/modern_draft.py inspect`. Select the main timeline through `Timelines/project.json`. On the verified Windows layout, prefer `draft_content.json` over stale `draft_info.json`.
2. Modify existing 11.x projects with `modern_draft.clone_edit` and a checked replacement plan. Preserve unknown JSON fields and file encodings. Work in a new folder. Never use the old `JyProject` serializer for app-saved multi-file projects.
3. Generate new projects with the prepared Windows runtime's `JyProject` APIs, a unique name, and `overwrite=False`. See [new-projects.md](references/new-projects.md). Verify opening and saving in the installed app.
4. Preview/export through observed desktop controls. The upstream exporter is not a verified 11.5 exporter. Check window identity, controls, output path and completion. Do not infer UI verification from a JSON roundtrip.

## Establish the environment

- Resolve the connected device and installed version through Windows uninstall metadata and the version folder. Set `JY_INSTALL_DIR` to the exact folder containing `videoeditor.dll`.
- Read the draft catalog or use the user-specified project path. Do not assume the default C: location is the actual draft root. Exclude recycled/cloud-cache folders unless requested.
- Deploy these scripts to a dedicated Windows runtime folder. For the full upstream APIs, prepare a new runtime with `scripts/prepare_runtime.py --source <clean-pinned-upstream-checkout> --destination <new-runtime-folder>`. The patch is bundled as text; upstream catalogs and dependencies stay in that runtime. Use 64-bit Python. Codec and copy editing require only the standard library. Invoke the native worker only in a short-lived child process through `draft_codec.py`.
- Exit Jianying normally before copying/editing files. Do not kill the app to bypass this check. UI inspection itself does not require closing it.
- If a main timeline is missing, plaintext malformed, native decoding fails, or multiple live timelines require editing, stop that write and report the specific problem. Never delete or auto-heal the source as a fallback.

## Inspect and create a review copy

Substitute observed paths in these PowerShell commands:

```powershell
$skillRoot = 'C:\Tools\jianying-editor-115' # replace with this installed skill folder
$env:JY_INSTALL_DIR = 'C:\Path\To\JianyingPro\11.5.0.14471' # observed DLL folder
python "$skillRoot\scripts\modern_draft.py" inspect 'D:\Drafts\Source'
python "$skillRoot\scripts\modern_draft.py" decode '<selected_file from inspect>' 'D:\Work\source-readonly.json'
python "$skillRoot\scripts\modern_draft.py" clone 'D:\Drafts\Source' 'D:\Drafts\Review-Copy' --patch 'D:\Work\patch.json'
```

Decode exclusively creates a new file. Clone refuses existing/overlapping destinations. Keep project edit plans and output videos outside the skill source folder.

Build the plan using `source_sha256` from inspection and exact JSON Pointers from the decoded authoritative timeline:

```json
{"source_sha256":"<observed hash>","operations":[{"op":"replace","path":"/tracks/0/segments/0/volume","expected":1.0,"value":0.8}]}
```

Use existing paths and observed expected values. Replace nested text `content` JSON as a complete string after updating text and style ranges together. For timing changes maintain source/target ranges, duration, keyframes and material references. Arbitrary JSON replacement is not semantic validation; review effects, captions and audio in the app.

Clone copies source files, verifies the snapshot, patches root/main timeline mirrors, assigns fresh project metadata, remaps internal media paths, validates encoded outputs, checks source hashes and then publishes the new folder. It does not automatically register the copy in the user's catalog.

## Acceptance

- Report file-level and native-app results separately.
- Require codec roundtrip, source unchanged and main timeline mirror checks for file-level success.
- To claim editing success, open the copy in the installed app, inspect/play the edit, save, exit normally, reopen and read the saved timeline again.
- To claim export success, inspect the actual video with ffprobe and a full decode check.
- Do not downgrade the app, patch its binary, remove material entitlements, run random decryption executables, or overwrite the original to finish a task.
