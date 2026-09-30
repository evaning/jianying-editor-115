# Third-party notices

This is an independent compatibility extension, not an official release by the upstream authors or Jianying.

| Component | Pinned source | License and inclusion |
| --- | --- | --- |
| Jianying Editor Skill v1.7.0 | https://github.com/luoluoluo22/jianying-editor-skill/tree/32c56928ded4f9e2c2b80e099dc7abb793d2c30b | MIT, Copyright (c) 2026 luoluoluo22. A compatibility patch is bundled; the complete repository is not. |
| jy-draftc native calling convention | https://github.com/wenshui330/jy-draftc/tree/d1c8a7dcb79c2f17f96ab95013a079e777fc236e | MIT, Copyright (c) 2026 wenshui330. Adapted native wrapper code is bundled. |
| pyJianYingDraft in optional upstream runtime | https://github.com/GuanYixuan/pyJianYingDraft | Apache-2.0, Copyright (c) 2024 GuanYixuan. Not vendored in the lightweight archive; its license is retained when preparing the optional runtime. |

The full MIT notices are under `skills/jianying-editor-115/references/LICENSE-upstream.txt` and `LICENSE-jy-draftc.txt`.

Modifications include version-aware encoding detection, native re-encryption with roundtrip checking, guarded copy editing, modern main-timeline selection, legacy serializer refusal, runtime preparation and tests. The original upstream exporter is not certified for Jianying 11.5 by this project.

Jianying's proprietary executables and DLLs are not included. Users supply their own installed application. References to product names identify interoperability targets only.
