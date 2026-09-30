# Compatibility and provenance

## Implementation

- Base: luoluoluo22/jianying-editor-skill v1.7.0, revision 32c56928ded4f9e2c2b80e099dc7abb793d2c30b, MIT. Retain LICENSE-upstream.txt; prepare_runtime.py also retains the upstream vendored pyJianYingDraft Apache-2.0 license in the Windows runtime.
- Native calling convention: adapted from wenshui330/jy-draftc revision d1c8a7dcb79c2f17f96ab95013a079e777fc236e, MIT; retain LICENSE-jy-draftc.txt. Its published table reaches Windows 11.4.2; this fork's 11.5 results come from an actual installation.
- Invoke exported EncryptUtils functions from the installed videoeditor.dll. Retain input buffers, check status, parse output JSON and verify encrypt/decrypt equality. Isolate each operation in a child process to contain ABI failures and reclaim DLL-owned buffers on exit.
- No application patching, key scraping, network decryption or paid-feature bypass is implemented.

## Verified boundary

- Windows x64, Jianying 11.5.0.14471: real encrypted draft_content.json and metadata decoded successfully. Re-encryption byte roundtrip and JSON equality passed.
- The app saves sparse JSON: omitted numeric timerange fields mean zero; preserve those omissions rather than rejecting a valid native file.
- Distinguish plaintext, Base64 JSON and opaque Base64 encryption candidates. Malformed plaintext fails without writing.
- Edit existing single-main-timeline projects as raw JSON in independent folders. Preserve modern fields and synchronize root/main mirrors, including stale plaintext mirrors.
- Preserve the caller's source-root spelling when remapping paths, including Windows 8.3 aliases; returned project paths use their canonical form.
- Retain old APIs for new plaintext generation. Block native projects from their serializer even with overwrite=True. Loading failure no longer recreates a project.
- Multiple active timelines, macOS encrypted I/O, all UI controls and unattended export are not implied by codec success. Verify separately.
- native_ui_verified remains false on clone output until a separate actual app interaction passes.

## Generation limits

The older generator uses an older schema/effect catalog. JSON generation does not prove support for every newer feature. Do not relabel new_version to force compatibility or reload app-saved projects through the old generator.

Sources:
- https://github.com/luoluoluo22/jianying-editor-skill
- https://github.com/wenshui330/jy-draftc

## Worker contract

Invoke draft_codec.native_transform, not DLL imports in a long-lived session. It uses private temporary files, a 45-second timeout, no shell interpolation and bounded file sizes. The worker exclusively creates output and never writes input. Native symbols may change: report failures, preserve sources and test the new version before claiming support.

## Validation record (2026-09-30)

14 focused regression tests passed. An independent use of the skill on a synthetic project changed clip volume in a fresh copy, retained unknown fields/media and verified original hashes and all mirrors. On a real Windows 11.5.0.14471 installation, an encrypted project copy opened and played in the native editor; a modified text payload survived native save, complete application exit, cold reopening in a new process and file readback. Main timeline/root content matched and all original project file hashes remained unchanged. This is not visual QA for every caption/effect. Native export remains unverified.

## Distribution

This installed skill contains the native codec, copy editor, regression suite and a text patch against the pinned upstream revision. prepare_runtime.py builds the full runtime from a clean local upstream checkout, preserving licenses. The user's already deployed runtime is independent of this lightweight skill folder.
