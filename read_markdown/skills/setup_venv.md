# Skill: setup_venv

## Purpose

Creates a Python virtual environment (.venv).

## When to Use

- Setting up a new Python project
- Isolating project dependencies
- Creating a clean Python environment for testing
- Preparing a project before installing packages

## Parameters

- `env_dir` (string, optional): Path where the virtual environment will be created. Defaults to `.venv` in the current directory.

## Example

```
setup_venv(".venv")
```

Creates a `.venv/` directory with Python's virtual environment inside.

## Returns

- Success message with the path to the created environment

## Related Skills

- `create_folder`: Create directories manually
- `create_file`: Create files inside the project
