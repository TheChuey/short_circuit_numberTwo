# Skill: create_folder

## Purpose

Creates a directory at the specified path.

## When to Use

- Setting up project directory structures
- Creating output directories before writing files
- Organizing files into folders
- Creating nested directory structures

## Parameters

- `folder_path` (string, required): Full path of the directory to create. Parent directories are created automatically if they don't exist.

## Example

```
create_folder("src/components")
```

Creates `src/components/` directory (and `src/` if it doesn't exist).

## Returns

- Success message with the created path

## Related Skills

- `create_file`: Create files inside the new folder
- `write_file`: Write files into the created directory
