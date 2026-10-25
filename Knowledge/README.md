# Zero AI — Local Knowledge Base

This folder serves as the local document library and knowledge base for Zero AI.

## Supported File Formats
Zero automatically scans and indexes the following document types:
- **Markdown:** `.md`, `.markdown`
- **Plain Text:** `.txt`
- **Adobe PDF:** `.pdf`
- **Microsoft Office:** `.docx`, `.pptx`, `.xlsx`

## Organizing Your Documents
You can organize your files into subfolders. Zero scans directories recursively:
```text
Knowledge/
├── 00_Inbox/
├── Projects/
├── Programming/
├── Cybersecurity/
├── Reference/
└── Personal-Notes/
```

## Privacy & Version Control Notice
- In `.gitignore`, all personal documents and large PDF files placed in this folder are **excluded from Git** by default.
- Only safe sample fixtures (such as `Zero_Evaluation_Fixture.txt` and `zero_architecture_overview.md`) are tracked for testing.
- Your personal documents will remain on your local computer and will **not** be pushed to GitHub.
