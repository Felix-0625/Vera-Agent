"""Check that local links, page assets, and in-page anchors resolve."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

SITE_ROOT = Path(__file__).resolve().parent
PAGES = (Path("index.html"), Path("docs/index.html"), Path("playground/index.html"))


class PageInspector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if element_id := attributes.get("id"):
            self.ids.add(element_id)
        for attribute in ("href", "src", "poster"):
            value = attributes.get(attribute)
            if value:
                self.links.append((tag, value))


def page_path(path: Path, url_path: str) -> Path:
    decoded = unquote(url_path)
    if not decoded or decoded.endswith("/"):
        decoded += "index.html"
    return (path.parent / decoded).resolve()


def main() -> int:
    failures: list[str] = []
    pages: dict[Path, PageInspector] = {}

    for relative_page in PAGES:
        file_path = (SITE_ROOT / relative_page).resolve()
        if not file_path.is_file():
            failures.append(f"missing page: {relative_page.as_posix()}")
            continue
        inspector = PageInspector()
        inspector.feed(file_path.read_text(encoding="utf-8"))
        pages[file_path] = inspector

    for file_path, inspector in list(pages.items()):
        for _tag, raw_url in inspector.links:
            parsed = urlsplit(raw_url)
            if parsed.scheme or parsed.netloc or raw_url.startswith("#"):
                if raw_url.startswith("#") and unquote(parsed.fragment) not in inspector.ids:
                    failures.append(f"{file_path.relative_to(SITE_ROOT)}: missing anchor {raw_url}")
                continue

            target = page_path(file_path, parsed.path)
            if SITE_ROOT not in target.parents and target != SITE_ROOT:
                failures.append(f"{file_path.relative_to(SITE_ROOT)}: link escapes site root: {raw_url}")
                continue
            if not target.is_file():
                failures.append(f"{file_path.relative_to(SITE_ROOT)}: missing local target {raw_url}")
                continue

            if parsed.fragment and target.suffix.lower() in {".html", ".htm"}:
                target_inspector = pages.get(target)
                if target_inspector is None:
                    target_inspector = PageInspector()
                    target_inspector.feed(target.read_text(encoding="utf-8"))
                    pages[target] = target_inspector
                anchor = unquote(parsed.fragment)
                if anchor not in target_inspector.ids:
                    failures.append(f"{file_path.relative_to(SITE_ROOT)}: missing anchor {raw_url}")

    if failures:
        print("Static site validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(f"Static site validation passed: {len(pages)} pages and local links/assets resolved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
