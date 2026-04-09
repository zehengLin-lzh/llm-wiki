# Schema: Research Notes

## Purpose
This knowledge base collects and organizes research materials, paper summaries, and learning notes.

## Entity Types
- **paper**: Academic papers and articles
- **author**: Researchers and authors
- **topic**: Research topics and fields
- **method**: Methods, algorithms, techniques
- **finding**: Key findings and results
- **dataset**: Datasets referenced in research

## Page Structure
- `concepts/` — research topics, fields, methods
- `entities/` — specific papers, authors, datasets
- `summaries/` — one summary per raw file
- `_reports/` — lint reports (auto-generated)

## Compilation Conventions
- Each raw file generates one summary in `summaries/`
- Extract key claims, methods, and findings
- Link papers to their authors, topics, and methods
- Note agreements and contradictions between sources
- `index.md` organizes by topic, then by recency
