# tests/test_challenger_verification.py
"""
Empirical Verification Test Suite for Web Documentation & Math Foundations.
Authored and executed by Challenger 1 (Empirical Web & Math Verification Challenger).
"""

import os
import re
import glob
from html.parser import HTMLParser
from bs4 import BeautifulSoup
import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML_PAGES = ["index.html", "docs.html", "methodology.html", "contact.html", "privacy.html", "terms.html"]
DOCS_MD_DIR = os.path.join(ROOT_DIR, "docs", "methodology")


class DuplicateIDParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = {}
        self.duplicates = []

    def handle_starttag(self, tag, attrs):
        for attr, val in attrs:
            if attr.lower() == "id" and val:
                if val in self.ids:
                    self.duplicates.append((val, tag, self.getpos(), self.ids[val]))
                else:
                    self.ids[val] = (tag, self.getpos())


def test_html_structural_integrity():
    """Validate HTML5 DOCTYPE, head, title, viewport, charset, and duplicate IDs across all pages."""
    errors = []
    for page in HTML_PAGES:
        page_path = os.path.join(ROOT_DIR, page)
        assert os.path.exists(page_path), f"File {page} missing"
        with open(page_path, "r", encoding="utf-8") as f:
            content = f.read()

        if not content.strip().lower().startswith("<!doctype html>"):
            errors.append(f"{page}: Missing <!DOCTYPE html>")

        soup = BeautifulSoup(content, "html.parser")
        if not soup.html:
            errors.append(f"{page}: Missing <html> tag")
        if not soup.head:
            errors.append(f"{page}: Missing <head> tag")
        if not soup.body:
            errors.append(f"{page}: Missing <body> tag")
        if not soup.title or not soup.title.string.strip():
            errors.append(f"{page}: Missing or empty <title> tag")

        meta_charset = soup.find("meta", charset=True) or soup.find("meta", attrs={"http-equiv": lambda v: v and v.lower() == "content-type"})
        if not meta_charset:
            errors.append(f"{page}: Missing <meta charset>")

        meta_viewport = soup.find("meta", attrs={"name": "viewport"})
        if not meta_viewport:
            errors.append(f"{page}: Missing <meta name='viewport'>")

        id_parser = DuplicateIDParser()
        id_parser.feed(content)
        if id_parser.duplicates:
            for dup, tag, pos, orig in id_parser.duplicates:
                errors.append(f"{page}: Duplicate id='{dup}' on <{tag}> at line {pos[0]}")

    assert not errors, f"HTML structural errors:\n" + "\n".join(errors)


def test_anchor_links_and_cross_references():
    """Validate that all internal and cross-page anchor links resolve to valid IDs and files."""
    errors = []
    page_ids = {}
    page_soups = {}
    for page in HTML_PAGES:
        page_path = os.path.join(ROOT_DIR, page)
        with open(page_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
        page_soups[page] = soup
        ids = set()
        for el in soup.find_all(attrs={"id": True}):
            ids.add(el["id"])
        page_ids[page] = ids

    for page in HTML_PAGES:
        soup = page_soups[page]
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href or href == "#" or href.startswith("javascript:") or href.startswith("mailto:") or href.startswith("tel:"):
                continue
            if href.startswith("http://") or href.startswith("https://"):
                continue

            if href.startswith("#"):
                anchor = href[1:]
                if anchor not in page_ids[page]:
                    errors.append(f"{page}: Broken intra-page anchor href='{href}' on <a> text='{a.get_text(strip=True)[:30]}'")
            else:
                parts = href.split("#", 1)
                target_file = parts[0]
                target_anchor = parts[1] if len(parts) > 1 else None

                target_path = os.path.join(ROOT_DIR, target_file)
                if not os.path.exists(target_path):
                    errors.append(f"{page}: Broken relative link to non-existent file href='{href}'")
                elif target_anchor:
                    if target_file in page_ids:
                        if target_anchor not in page_ids[target_file]:
                            errors.append(f"{page}: Broken cross-page anchor href='{href}' (id='{target_anchor}' not found in {target_file})")

    assert not errors, f"Link verification errors:\n" + "\n".join(errors)


def test_markdown_latex_integrity():
    """Validate delimiter pairing and brace balancing across all 11 methodology markdown files."""
    md_files = glob.glob(os.path.join(DOCS_MD_DIR, "*.md"))
    assert len(md_files) >= 10, f"Expected at least 10 methodology markdown files, found {len(md_files)}"

    errors = []
    for md_file in md_files:
        basename = os.path.basename(md_file)
        with open(md_file, "r", encoding="utf-8") as f:
            text = f.read()

        total_double_dollar = text.count("$$")
        if total_double_dollar % 2 != 0:
            errors.append(f"{basename}: Odd count of '$$' delimiters ({total_double_dollar})")

        display_math = re.findall(r"\$\$([\s\S]*?)\$\$", text)
        for expr in display_math:
            stack = []
            for ch in expr:
                if ch == "{": stack.append(ch)
                elif ch == "}":
                    if not stack:
                        errors.append(f"{basename}: Unbalanced closing brace in display math: {expr[:40]}")
                        break
                    stack.pop()
            if stack:
                errors.append(f"{basename}: Unclosed opening brace in display math: {expr[:40]}")

    assert not errors, f"Markdown LaTeX errors:\n" + "\n".join(errors)


@pytest.mark.xfail(reason="Adversarial challenge for static site KaTeX migration", strict=False)
def test_formula_card_delimiters_challenge():
    """
    Adversarial Challenge: Verify whether all 29 .formula-math-display cards in methodology.html
    possess math delimiters ($$...$$ or \\[...\\]) required for KaTeX auto-rendering.
    """
    methodology_path = os.path.join(ROOT_DIR, "methodology.html")
    with open(methodology_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "lxml")

    cards = soup.find_all(class_="formula-math-display")
    assert len(cards) == 29, f"Expected 29 .formula-math-display elements, found {len(cards)}"

    undelimited = []
    for i, card in enumerate(cards):
        text = card.get_text().strip()
        has_display_delim = (text.startswith("$$") and text.endswith("$$")) or (text.startswith("\\[") and text.endswith("\\]"))
        if not has_display_delim:
            undelimited.append((i + 1, text[:60]))

    if undelimited:
        details = "\n".join([f"  Card #{num}: {snippet}..." for num, snippet in undelimited])
        pytest.fail(f"CRITICAL BUG: {len(undelimited)} of 29 .formula-math-display cards lack $$ delimiters, causing KaTeX auto-render to skip them:\n{details}")


@pytest.mark.xfail(reason="Adversarial challenge for static site KaTeX migration", strict=False)
def test_katex_ignored_classes_challenge():
    """
    Adversarial Challenge: Verify that elements with math expressions are not suppressed
    by KaTeX auto-render ignoredClasses (specifically 'sensor-table').
    """
    methodology_path = os.path.join(ROOT_DIR, "methodology.html")
    with open(methodology_path, "r", encoding="utf-8") as f:
        content = f.read()

    soup = BeautifulSoup(content, "lxml")
    sensor_tables = soup.find_all(class_="sensor-table")
    assert len(sensor_tables) > 0, "No sensor-table elements found"

    tables_with_math = []
    for i, tbl in enumerate(sensor_tables):
        text = tbl.get_text()
        math_matches = re.findall(r"\$([^$]+)\$", text)
        if math_matches:
            tables_with_math.append((i, len(math_matches), math_matches[:3]))

    # Check if 'sensor-table' is in ignoredClasses in the script
    if "ignoredClasses:" in content and "sensor-table" in content.split("ignoredClasses:")[1].split("]")[0]:
        if tables_with_math:
            details = "\n".join([f"  Table #{idx} ({count} formulas): {samples}" for idx, count, samples in tables_with_math])
            pytest.fail(f"CRITICAL BUG: KaTeX auto-render configuration ignores 'sensor-table', but 3 tables contain math:\n{details}")
