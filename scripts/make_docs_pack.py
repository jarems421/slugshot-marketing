"""Build exports/share/chatgpt-pack/Slugshot-Claude-Toolkit-Docs.md: one file to upload to ChatGPT and Gemini.

Intro from docs/pack-intro.md ({{GENERATED}} is replaced with the date and commit), then each file below in
full. Re-run after any doc change: `.venv\\Scripts\\python scripts\\make_docs_pack.py`.
"""
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "exports" / "share" / "chatgpt-pack" / "Slugshot-Claude-Toolkit-Docs.md"
FILES = [
    ("README.md", "project overview, architecture, capabilities, setup"),
    ("docs/OPERATIONS.md", "operator walkthrough: commands, folders, CSV schemas, safety rails"),
    ("docs/COMMANDS.md", "every command"),
    ("docs/research-data.md", "research collectors: commands, routine, schemas, sharing rules, TikTok and Trends API findings"),
    ("docs/research-data-audit.md", "Stage 4.4 source audit, decisions and outcome"),
    (".claude/skills/slugshot-research-operations/SKILL.md", "research operations skill: how Claude runs research from a short instruction"),
    ("docs/stage-4.5.4-report.md", "Stage 4.5.4 configuration and first 4.5.5 pilot: results and recommended changes"),
    ("docs/chatgpt-research-skills-v1.1.md", "ChatGPT research skills v1.1: local reference copy Claude follows, operating decisions, remaining milestones"),
    ("docs/composio.md", "Composio integration: what is installed, tested, audited and what needs owner authorisation"),
    ("docs/chatgpt-handoff-4.5.3.md", "Stage 4.5.3 handoff: what Claude implemented, bundle format, ledger names, recommended skill changes"),
    (".claude/skills/slugshot-research-analysis/SKILL.md", "research analysis skill: intake, statistics, trends, coding, ledger"),
    ("docs/research-evidence.md", "evidence ledger: fields, statuses, strength, validator checks, example"),
    ("docs/research-methods.md", "research methods: contract, inference ladder, independence, sampling, analysis, trends, coding, EN/ES, literature"),
    ("research/schemas/evidence-ledger.schema.json", "evidence ledger JSON Schema"),
    ("research/templates/research-brief.md", "research brief template (ChatGPT -> Claude)"),
    ("research/templates/decision-memo.md", "decision memo template"),
    ("research/upstream/PROVENANCE.md", "upstream components: commits, licences, decisions"),
    ("config/research/codebooks/slugshot-creative.json", "creative codebook v1.1 (ChatGPT; v1.0 archived for the first pilot)"),
    ("config/research/query_families.json", "Stage 4.5.4 query family structure (starter)"),
    ("roblox-native/README.md", "Roblox-native production (place, guard, runner, tests, decisions)"),
    (".claude/skills/slugshot-roblox-production/SKILL.md", "Roblox production skill"),
    (".claude/skills/slugshot-roblox-production/references/scene-specs.md", None),
    (".claude/skills/slugshot-roblox-production/references/studio-safety.md", None),
    (".claude/skills/slugshot-roblox-production/references/capture-and-handoff.md", None),
    ("docs/flow-and-gemini.md", "Flow and Gemini hand-offs"),
    ("docs/INVENTORY.md", "installed software and capability status"),
    (".claude/skills/slugshot-video-editing/SKILL.md", "video editing skill"),
    (".claude/skills/slugshot-video-editing/references/script-to-edit.md", None),
    (".claude/skills/slugshot-video-editing/references/pacing-cuts-zooms.md", None),
    (".claude/skills/slugshot-video-editing/references/captions-and-hierarchy.md", None),
    (".claude/skills/slugshot-video-editing/references/audio-design.md", None),
    (".claude/skills/slugshot-video-editing/references/format-playbooks.md", None),
    (".claude/skills/slugshot-video-editing/references/review-and-approval.md", None),
    ("docs/game-truth.md", "game truth for marketing claims"),
    ("docs/youtube-api-policy.md", "YouTube API rules"),
    ("docs/production-checklist.md", "deferred production work"),
    ("reports/smoke-test.md", "latest full smoke test"),
    ("reports/smoke-test-research.md", "latest research smoke test"),
    ("CLAUDE.md", "Claude Code brief and working notes"),
    ("config/research/settings.json", "research collector settings (no secrets)"),
    ("config/research/youtube_queries.json", "saved YouTube query sets (test set only)"),
    ("data/templates/public_observations_template.csv", "observation import template"),
    ("data/templates/examples/observations_creative_center.csv", "example: Creative Center hashtags"),
    ("data/templates/examples/observations_vidiq.csv", "example: vidIQ rows"),
    ("data/templates/examples/observations_chatgpt_table.md", "example: a pasted ChatGPT table"),
    ("roblox-native/scenes/smoke/smoke_floppy_standin.json", "example scene spec"),
    ("jobs/edit-sample-story.json", "example edit file"),
    ("jobs/sample-variants.json", "example variants job"),
    ("jobs/scripts/sample-story.md", "example approved script"),
]
FENCE = {".json": "json", ".csv": "csv"}


def main():
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    gen = f"Generated {stamp} from the slugshot-marketing repo (commit {commit}{' plus uncommitted changes' if dirty else ''})."
    parts = [(ROOT / "docs" / "pack-intro.md").read_text(encoding="utf-8").replace("{{GENERATED}}", gen).rstrip(), "", "## Contents", ""]
    parts += [f"{n}. {p}" + (f": {d}" if d else "") for n, (p, d) in enumerate(FILES, 1)]
    for path, _ in FILES:
        text = (ROOT / path).read_text(encoding="utf-8-sig").replace("\r\n", "\n").rstrip()
        lang = FENCE.get(Path(path).suffix)
        body = f"```{lang}\n{text}\n```" if lang else text
        parts += ["", "---", "", f"<!-- FILE: {path} -->", "", body]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(parts) + "\n", encoding="utf-8")
    print(f"{OUT} ({len(FILES)} files, {OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
