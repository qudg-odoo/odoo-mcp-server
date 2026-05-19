from pathlib import Path


def _parse_frontmatter(text):
    meta = {}
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            for line in text[3:end].strip().splitlines():
                if ":" in line:
                    key, _, val = line.partition(":")
                    meta[key.strip()] = val.strip()
    return meta


def list_skills(skills_dir):
    directory = Path(skills_dir)
    if not directory.is_dir():
        return []
    out = []
    for path in sorted(directory.glob("*.md")):
        meta = _parse_frontmatter(path.read_text(encoding="utf-8"))
        out.append({
            "name": meta.get("name", path.stem),
            "description": meta.get("description", ""),
        })
    return out


def get_skill(skills_dir, name):
    path = Path(skills_dir) / f"{name}.md"
    if not path.is_file():
        raise FileNotFoundError(f"Skill '{name}' introuvable.")
    return path.read_text(encoding="utf-8")
