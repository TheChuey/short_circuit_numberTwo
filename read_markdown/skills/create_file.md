# Skill: create_file

## Purpose

Creates a new file with optional initial content.

## When to Use

- Creating new source files during project scaffolding
- Writing configuration files (e.g., `.env`, `config.json`)
- Generating output files from templates
- Creating empty placeholder files

## Parameters

- `file_path` (string, required): Full path to the file to create. Parent directories are created automatically if they don't exist.
- `content` (string, optional): Initial content to write to the file. Defaults to empty string.

## Example

```
create_file("src/main.py", "print('Hello, World!')")
```

Creates `src/main.py` with the content `print('Hello, World!')`.

## Related Skills

- `write_file`: Overwrites an existing file with new content
- `create_folder`: Creates a directory (useful if you need the parent folder first)
- `read_file`: Read the contents of a file after creating it
