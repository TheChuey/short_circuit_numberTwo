# Agents Index

> Global listing of all agents defined in this project.
> Each agent has its own definition file. Shared skill documentation lives in `skills/`.

## Agents

| Agent | File | Type | Model | Purpose |
|---|---|---|---|---|
| AI Agent Development Assistant | [chat_bot_agent.md](chat_bot_agent.md) | Chatbot | gemma4:e2b | Help the user learn AI agents and build them with Python |
| Chat (Basic) | [chat_bot_basic.md](chat_bot_basic.md) | Basic | (none) | Minimal fallback chatbot with no tools |

## Skills Reference

Detailed documentation for shared skills lives in `skills/`:

| Skill | Description | Docs |
|---|---|---|
| create_file | Creates a new file with optional initial content | [details](skills/create_file.md) |
| read_file | Reads and returns contents of a text file | [details](skills/read_file.md) |
| write_file | Writes or overwrites text content to a file | [details](skills/write_file.md) |
| create_folder | Creates a directory at the specified path | [details](skills/create_folder.md) |
| setup_venv | Creates a Python virtual environment | [details](skills/setup_venv.md) |
| read_pdf | Extracts text contents from a PDF file | [details](skills/read_pdf.md) |
| get_current_date | Return the real current date as a formatted string | [details](skills/get_current_date.md) |
| tell_me_the_date_and_time | Returns the current date and time | [details](skills/tell_me_the_date_and_time.md) |

## Adding a New Agent

1. Create a new file: `read_markdown/{agent_name}.md`
2. Follow the format in `chat_bot_agent.md`
3. List the agent in this index
4. Add the agent to `read_markdown/markdown_loader.py` (create a new loader instance)
5. Restart the server

## Adding a New Skill

1. Create a new file: `read_markdown/skills/{skill_id}.md`
2. Follow the format in `skills/_header.md`
3. Add the skill function to `app/tools/tools.py` SKILL_REGISTRY
4. Add the skill to the relevant agent's `## skills` table
5. Restart the server
