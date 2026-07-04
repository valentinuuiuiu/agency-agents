import os
import json
from pathlib import Path

def get_frontmatter_field(content, field):
    lines = content.split('\n')
    in_fm = False
    for line in lines:
        if line.strip() == '---':
            if in_fm: break
            in_fm = True
            continue
        if in_fm and line.startswith(f"{field}:"):
            val = line.split(':', 1)[1].strip()
            return val.strip('"').strip("'")
    return ""

def main():
    repo_root = Path(__name__).parent.parent.absolute()
    divisions = ["academic", "design", "engineering", "finance", "game-development", "gis", "marketing", "paid-media", "product", "project-management", "sales", "security", "spatial-computing", "specialized", "support", "testing"]

    manifest = []

    for div in divisions:
        div_path = repo_root / div
        if not div_path.is_dir():
            continue

        for file_path in div_path.glob("*.md"):
            content = file_path.read_text(errors='ignore')
            if not content.startswith('---'):
                continue

            name = get_frontmatter_field(content, "name")
            if not name: continue

            emoji = get_frontmatter_field(content, "emoji")
            description = get_frontmatter_field(content, "description")
            slug = file_path.stem
            if '-' in slug:
                slug = slug.split('-', 1)[1]

            manifest.append({
                "name": name,
                "emoji": emoji,
                "slug": slug,
                "division": div,
                "description": description
            })

    with open(repo_root / "agents-manifest.json", "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"Manifest generated: {repo_root / 'agents-manifest.json'} ({len(manifest)} agents)")

if __name__ == "__main__":
    main()
