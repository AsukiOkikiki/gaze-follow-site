#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把精灵图集 atlas.jpg 内联进 HTML 模板 -> 单文件 index.html（零外部依赖）。

用法:
  python build.py --template index.template.html --atlas atlas.jpg --out index.html
默认（参数省略时）: 当前目录下 index.template.html + atlas.jpg -> index.html

模板中必须含占位符 __ATLAS_B64__，会被 atlas 的 base64 替换。
"""
import argparse
import base64
import pathlib


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", default="index.template.html")
    ap.add_argument("--atlas", default="atlas.jpg")
    ap.add_argument("--out", default="index.html")
    a = ap.parse_args()

    tpl_path = pathlib.Path(a.template)
    atlas_path = pathlib.Path(a.atlas)
    if not tpl_path.exists():
        raise SystemExit("找不到模板: %s" % tpl_path)
    if not atlas_path.exists():
        raise SystemExit("找不到图集: %s" % atlas_path)

    tpl = tpl_path.read_text(encoding="utf-8")
    if "__ATLAS_B64__" not in tpl:
        raise SystemExit("模板里找不到 __ATLAS_B64__ 占位符")
    b64 = base64.b64encode(atlas_path.read_bytes()).decode("ascii")
    out = tpl.replace("__ATLAS_B64__", b64)

    out_path = pathlib.Path(a.out)
    out_path.write_text(out, encoding="utf-8", newline="\n")
    size = out_path.stat().st_size
    print("atlas     : %8d bytes" % atlas_path.stat().st_size)
    print("html      : %8d bytes (%.2f MB)" % (size, size / 1e6))


if __name__ == "__main__":
    main()
