#!/usr/bin/env python3
"""
Generate BibTeX software citations for the Python packages your project actually uses.

Usage:
  python cite_software.py /path/to/your/project > software.bib

Notes:
- Scans *.py files for imports, maps module -> installed distribution name via importlib.metadata,
  then renders @software BibTeX entries with version, author (if available), URL, and (optional) DOI.
- You can optionally add packages manually via --add package1 package2 ...
- For packages that publish a recommended citation or DOI (e.g., pandas), we include it.
"""

import argparse, os, re, sys, json
from pathlib import Path

try:
    from importlib import metadata as m  # py3.8+
except Exception:
    import importlib_metadata as m  # type: ignore

DOI_HINTS = {
    # Common scientific packages with DOIs
    "pandas": "10.5281/zenodo.3509134",
    # Add more as needed, e.g. "numpy": "10.1038/s41586-020-2649-2" (paper), etc.
}

STD_NAMES = set(getattr(sys, "stdlib_module_names", set()))  # py3.10+; empty on older versions

IMPORT_RE = re.compile(r'^\s*(?:from\s+([a-zA-Z0-9_\.]+)\s+import|import\s+([a-zA-Z0-9_\.]+))', re.M)

def find_import_roots(root: Path):
    roots = set()
    for p in root.rglob("*.py"):
        try:
            s = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for mobj in IMPORT_RE.finditer(s):
            mod = (mobj.group(1) or mobj.group(2) or "").strip()
            if not mod:
                continue
            top = mod.split(".")[0]
            if top and top not in STD_NAMES:
                roots.add(top)
    return roots

def roots_to_distributions(roots):
    # Map import roots to installed distribution names
    pkg_map = m.packages_distributions()  # {module: [dist,...]}
    dists = set()
    for r in sorted(roots):
        candidates = pkg_map.get(r, [])
        if candidates:
            # Heuristic: prefer the first candidate
            dists.add(candidates[0])
        else:
            # Some projects install under the same name as the module
            dists.add(r)
    return dists

def bibtex_key(name, version):
    base = (name or "").lower().replace(" ", "-")
    ver  = (version or "").replace(" ", "-")
    return f"{base}-{ver}" if ver else base

def entry_for(dist_name):
    try:
        md = m.metadata(dist_name)
    except m.PackageNotFoundError:
        # Fall back to "module only" entry
        return {
            "name": dist_name,
            "version": "",
            "author": "Project contributors",
            "url": "",
            "doi": DOI_HINTS.get(dist_name.lower(), ""),
        }
    name = md.get("Name", dist_name)
    version = md.get("Version", "")
    author = (md.get("Author") or md.get("Maintainer") or "Project contributors")
    url = (md.get("Home-page") or "")
    doi = DOI_HINTS.get(name.lower(), "")
    return {"name": name, "version": version, "author": author, "url": url, "doi": doi}

def render_bib(e: dict):
    key = bibtex_key(e["name"], e["version"])
    fields = []
    fields.append(f"  title   = {{{e['name']}}}")
    fields.append(f"  author  = {{{e['author']}}}")
    if e.get("version"):
        fields.append(f"  version = {{{e['version']}}}")
    # GOOD
    # fields.append("  year    = { }  % fill in")
    
    if e.get("doi"):
        fields.append(f"  doi     = {{{e['doi']}}}")
    if e.get("url"):
        fields.append(f"  url     = {{{e['url']}}}")
    fields.append(f"  note    = {{Python package}}")
    return "@software{{{key},\n{body}\n}}".format(key=key, body=",\n".join(fields))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project_root", help="Path to your project (folder containing *.py)")
    ap.add_argument("--add", nargs="*", default=[], help="Extra packages to include (e.g., uvicorn numpy)")
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    roots = find_import_roots(root)
    # Exclude your own top-level package names (heuristic)
    for mine in list(roots):
        if (root / mine).exists():
            roots.discard(mine)

    dists = roots_to_distributions(roots) | set(args.add or [])
    # Always include Python itself
    entries = [{
        "name": "Python",
        "version": f"{sys.version_info.major}.{sys.version_info.minor}",
        "author": "Python Software Foundation",
        "url": "https://www.python.org/",
        "doi": "",
    }]

    for d in sorted(dists):
        entries.append(entry_for(d))

    for e in entries:
        print(render_bib(e))
        print()

if __name__ == "__main__":
    main()
