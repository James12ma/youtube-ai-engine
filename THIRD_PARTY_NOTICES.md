# Third-party notices

## youtube-agent-skill

Portions of the following LogicScript files are adapted from
[Jakeschincariol/youtube-agent-skill](https://github.com/Jakeschincariol/youtube-agent-skill)
at commit `a2feb2104981a375ffd4f87ee04f4f5344ac43c6`:

| LogicScript file | Adapted from | Changes |
|---|---|---|
| `channel/packaging_lint.py` | `skills/yt-package/title.py` | configurable policy with blocking/advisory split, plural-insensitive duplicate check, number hint reworded for citation policy |
| `channel/chapters.py` (validation rules only) | `skills/yt-chapters/chapters.py` | boundaries come from LogicScript's narration timeline, not pause detection |
| `pipeline/hook_score.py` | `skills/yt-script/hookscore.py` | advisory-only API; specificity suggestion no longer asks for numbers |
| `pipeline/hook_formulas.json` | `skills/yt-script/hooks.json` | unmodified data plus an attribution field |

The project is not installed as a dependency or plugin; only the code above was ported.

```
MIT License

Copyright (c) 2026 Jake Schincariol

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
