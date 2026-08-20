# Skills Documentation

> This folder contains detailed documentation for each shared skill available to agents.

## Purpose

Each `.md` file in this folder describes one skill (tool) that agents can use. These docs explain:

- What the skill does
- When to use it
- What parameters it accepts
- How to use it correctly
- Related skills

## How This Folder Works

- **One file per skill** — named `{skill_id}.md` (e.g., `create_file.md`, `read_file.md`)
- **Shared across all agents** — any agent can reference any skill in this folder
- **Parsed at startup** — `markdown_loader.py` reads these files and generates `config/skills.json`
- **Agent skills table** — each agent definition file (`chat_bot_agent.md`) has a brief skills table that links to these detailed docs

## File Format

Each skill file follows this structure:

```markdown
# Skill: {skill_name}

## Purpose
One-line description of what the skill does.

## When to Use
- Bullet list of scenarios where this skill is useful

## Parameters
- `param_name` (type, required/optional): Description

## Example
Brief usage example.

## Related Skills
- other_skill: How it relates
```

## Adding a New Skill

1. Create a new file: `read_markdown/skills/{skill_id}.md`
2. Follow the format above
3. Add the skill function to `app/tools/tools.py` SKILL_REGISTRY
4. Add the skill to the agent's `## skills` table in `chat_bot_agent.md`
5. Restart the server — `markdown_loader.py` regenerates `skills.json`
