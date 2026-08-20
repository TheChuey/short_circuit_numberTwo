# Skill: write_file

## Purpose

Writes or overwrites text content to a file.

## When to Use

- Updating existing file contents
- Overwriting configuration files with new values
- Saving generated output to a file
- Replacing entire file contents

## Parameters

- `file_path` (string, required): Full path to the file to write.
- `content` (string, required): The content to write to the file.

## Example

```
write_file("config/settings.json", '{"theme": "dark"}')
```

Writes `{"theme": "dark"}` to `config/settings.json`, overwriting any existing content.

## Related Skills

- `create_file`: Create a new file (with optional initial content)
- `read_file`: Read file contents before overwriting
- `create_folder`: Create parent directories if needed
