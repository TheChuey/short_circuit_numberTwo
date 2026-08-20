# Skill: read_file

## Purpose

Reads and returns the contents of a text file.

## When to Use

- Inspecting the contents of a source file
- Reading configuration files
- Checking if a file exists and what it contains
- Loading template files

## Parameters

- `file_path` (string, required): Full path to the file to read.

## Example

```
read_file("src/main.py")
```

Returns the full text content of `src/main.py`.

## Returns

- The file's text content as a string
- An error message if the file does not exist

## Related Skills

- `write_file`: Write or overwrite file contents
- `create_file`: Create a new file with initial content
- `read_pdf`: Read contents of PDF files specifically
