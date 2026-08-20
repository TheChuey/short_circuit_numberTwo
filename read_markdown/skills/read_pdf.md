# Skill: read_pdf

## Purpose

Extracts text contents from a PDF file.

## When to Use

- Reading text from PDF documents
- Extracting content from research papers
- Processing PDF reports or manuals
- Analyzing PDF-based documentation

## Parameters

- `pdf_path` (string, required): Full path to the PDF file to read.

## Example

```
read_pdf("documents/report.pdf")
```

Returns the extracted text content from all pages of the PDF.

## Returns

- The extracted text content as a string
- An error message if `pypdf` is not installed or the file doesn't exist

## Requirements

- The `pypdf` library must be installed (`pip install pypdf`)

## Related Skills

- `read_file`: Read text files (non-PDF)
- `write_file`: Write extracted content to a text file
