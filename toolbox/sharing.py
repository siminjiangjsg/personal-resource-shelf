"""Standalone exports built only from the public share schema."""

import re
from html import escape
from typing import Final
from urllib.parse import quote

from toolbox.models import Collection

SHARE_CSS: Final = """
:root{color-scheme:light dark;--bg:light-dark(#fff,#20211f);
--fg:light-dark(#31302e,#f2f0ec);--muted:light-dark(#615d59,#bab6af);
--line:light-dark(#dedbd6,#474842);--link:light-dark(#005bab,#a8d4fc)}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);
font:16px/1.7 'Segoe UI','Microsoft YaHei',system-ui,sans-serif}
main{max-width:760px;margin:auto;padding:48px 24px}
h1{font-size:28px;line-height:1.4;overflow-wrap:anywhere}h2{font-size:19px;margin:0}
article{padding:24px 0;border-top:1px solid var(--line)}
a{color:var(--link);overflow-wrap:anywhere}p{white-space:pre-wrap;overflow-wrap:anywhere}
.meta{color:var(--muted);font-size:14px}footer{margin-top:32px;color:var(--muted);font-size:14px}
@media(max-width:480px){main{padding:24px 16px}h1{font-size:24px}}
"""


def share_html(collection: Collection) -> str:
    entries: list[str] = []
    for item in collection.items:
        tags = ""
        if collection.show_tags and item.tags:
            tags = '<p class="meta">' + escape(" · ".join(item.tags)) + "</p>"
        recommendation = "<p>" + escape(item.recommendation) + "</p>" if item.recommendation else ""
        entries.append(
            "<article><h2>" + escape(item.title) + "</h2>"
            '<a target="_blank" rel="noopener noreferrer" href="'
            + escape(item.url, quote=True)
            + '">'
            + escape(item.url)
            + "</a>"
            + recommendation
            + tags
            + "</article>"
        )
    title = escape(collection.title)
    return (
        '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="referrer" content="no-referrer">'
        '<meta http-equiv="Content-Security-Policy" '
        'content="default-src &#39;none&#39;; style-src &#39;unsafe-inline&#39;; '
        'base-uri &#39;none&#39;; form-action &#39;none&#39;">'
        "<title>" + title + "</title><style>" + SHARE_CSS + "</style></head><body><main>"
        '<p class="meta">精选资源清单</p><h1>' + title + "</h1>"
        '<p class="meta">'
        + str(len(collection.items))
        + " 项资源</p>"
        + "".join(entries)
        + "<footer>整理与推荐 · 我的工具箱</footer></main></body></html>"
    )


def markdown_text(text: str) -> str:
    return re.sub(r"([\\\x60*_{}\[\]()<>#+.!|~-])", r"\\\1", text)


def share_markdown(collection: Collection) -> str:
    lines = ["# " + markdown_text(collection.title), ""]
    for item in collection.items:
        url = quote(item.url, safe=":/?#[]@!$&'()*+,;=%-._~")
        lines.extend(["## " + markdown_text(item.title), "", "<" + url + ">", ""])
        if item.recommendation:
            lines.extend([markdown_text(item.recommendation), ""])
        if collection.show_tags and item.tags:
            lines.extend(["标签：" + markdown_text("、".join(item.tags)), ""])
    return "\n".join(lines)


def download_headers(filename: str) -> dict[str, str]:
    return {"Content-Disposition": "attachment; filename*=UTF-8''" + quote(filename)}
