# New project generation

Prepare a full runtime first with scripts/prepare_runtime.py from a clean checkout of https://github.com/luoluoluo22/jianying-editor-skill at revision 32c56928ded4f9e2c2b80e099dc7abb793d2c30b. This skill ships the compatibility patch, not the large upstream catalogs. The already prepared Windows runtime can be reused.

Use that runtime only for a unique new project not yet saved by Jianying. Media generation can use ffprobe. Install additional dependencies in a dedicated virtual environment only when required. Codec/copy editing uses the standard library.

```python
import sys
sys.path.insert(0, r'C:\Tools\jianying-full-runtime\scripts')  # observed prepared runtime
from jy_wrapper import JyProject
project = JyProject('Unique_New_Project', drafts_root=r'D:\Drafts', overwrite=False)
project.add_clip(r'D:\Media\clip.mp4', source_start='0s', duration='3s', target_start='0s')
project.add_text_simple('Review title', start_time='0s', duration='3s')
project.save()
```

Read relevant rules/media.md, rules/text.md, rules/keyframes.md or rules/effects.md. These are upstream recipes; current native-project routing and no-destructive-fallback instructions take precedence. Recording/web-capture recipes may reference tools not bundled here; do not claim they are installed.

Verify the chosen operation before building a whole timeline. Review in the installed app. Once it creates Timelines/ or encrypted files, switch to modern_draft.py for subsequent changes.
