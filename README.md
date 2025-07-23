# PDF Outline Extractor - Challenge 1A

## Overview

This solution extracts structured outlines from PDF documents without requiring internet access, APIs, or LLMs. It analyzes font sizes, formatting, and text patterns to identify document titles and hierarchical headings (H1, H2, H3).

## Approach

### 1. Text Extraction with Formatting
- Uses **PyMuPDF (fitz)** library for robust PDF text extraction
- Preserves font size, style, and positioning information
- Extracts text blocks with their metadata for analysis

### 2. Heading Detection Strategy
The solution employs multiple heuristics to identify headings:

#### Font-Based Detection
- Analyzes font sizes across the document
- Identifies text with larger fonts than body text
- Detects bold formatting (font flags)

#### Pattern-Based Detection
- Numbered headings: `1.`, `1.1`, `1.1.1`, etc.
- Chapter/Section patterns: `Chapter 1`, `Section 2.1`
- Roman numerals: `I.`, `II.`, `III.`
- Letter patterns: `A.`, `B.`, `C.`
- Simple numbered formats: `1 Introduction`, `2 Overview`

#### Content-Based Heuristics
- Capitalized text with appropriate length
- Text ending with colons
- All-caps short text
- Text without common non-heading words

### 3. Heading Level Determination
- **H1**: Main sections, largest font sizes, simple numbering
- **H2**: Subsections, medium font sizes, numbered with one dot
- **H3**: Sub-subsections, smaller fonts, numbered with two dots

### 4. Title Extraction
- Analyzes first few pages for title candidates
- Prioritizes largest font sizes
- Scores candidates based on position, keywords, and format
- Fallback to first significant text if no clear title found

## Libraries Used

### Core Dependencies
- **PyMuPDF (fitz) 1.23.22**: High-performance PDF processing library
  - Extracts text with formatting information
  - Handles complex PDF layouts
  - Lightweight and fast (< 50MB)
  
- **regex 2023.12.25**: Enhanced regular expressions for pattern matching
  - Improves heading pattern detection
  - Better Unicode support for multilingual content

### Why These Libraries?
- **Offline Operation**: No network dependencies
- **Performance**: Optimized for speed and memory efficiency
- **Accuracy**: Preserves formatting crucial for heading detection
- **Size Constraint**: Combined size well under 200MB limit
- **Cross-platform**: Works reliably on AMD64 architecture

## Architecture

```
PDFOutlineExtractor
├── extract_text_with_formatting()  # Extract text + metadata
├── analyze_font_sizes()            # Determine font hierarchies
├── is_likely_heading()             # Heuristic heading detection
├── determine_heading_level()       # Assign H1/H2/H3 levels
├── extract_title()                 # Find document title
├── clean_heading_text()            # Normalize heading text
└── extract_outline()               # Main orchestration method
```

## Performance Optimizations

1. **Efficient Text Processing**: Single-pass document analysis
2. **Memory Management**: Process pages incrementally
3. **Duplicate Removal**: Avoid repeated headings
4. **Length Limiting**: Cap outline at 50 entries for performance
5. **Error Handling**: Graceful fallbacks for problematic PDFs

## Build and Run Instructions

### Building the Docker Image
```bash
docker build --platform linux/amd64 -t pdf-outline-extractor .
```

### Running the Solution
```bash
docker run --rm \
  -v $(pwd)/input:/app/input:ro \
  -v $(pwd)/output:/app/output \
  --network none \
  pdf-outline-extractor
```

### Expected Directory Structure
```
input/           # Place PDF files here
├── document1.pdf
├── document2.pdf
└── ...

output/          # JSON results appear here
├── document1.json
├── document2.json
└── ...
```

## Output Format

Each PDF generates a JSON file with this structure:

```json
{
  "title": "Document Title",
  "outline": [
    {
      "level": "H1",
      "text": "Main Section",
      "page": 0
    },
    {
      "level": "H2", 
      "text": "Subsection",
      "page": 1
    },
    {
      "level": "H3",
      "text": "Sub-subsection", 
      "page": 2
    }
  ]
}
```

## Key Features

### Robust PDF Handling
- Handles various PDF layouts and formats
- Works with scanned PDFs (if text is extractable)
- Graceful handling of corrupted or unusual PDFs

### Multilingual Support
- Unicode-aware text processing
- Pattern detection works across languages
- Proper encoding handling in JSON output

### Performance Compliance
- Processes 50-page PDFs in under 10 seconds
- Memory usage stays within 16GB limit
- CPU-efficient algorithms
- No GPU dependencies

### Offline Operation
- No internet connectivity required
- All processing done locally
- No external API calls or model downloads

## Error Handling

- **File Access Errors**: Gracefully skip problematic files
- **Parsing Errors**: Return empty outline for unparseable PDFs
- **Memory Issues**: Implemented safeguards and limits
- **Format Issues**: Robust fallbacks for edge cases

## Testing Strategy

The solution has been designed to handle:
- **Simple PDFs**: Basic documents with clear hierarchies
- **Complex PDFs**: Multi-column layouts, mixed content
- **Large PDFs**: Up to 50 pages within time constraints
- **Edge Cases**: Malformed or unusual PDF structures

## Constraints Compliance

✅ **Execution Time**: ≤ 10 seconds for 50-page PDFs  
✅ **Model Size**: ≤ 200MB (libraries only, no ML models)  
✅ **Network**: No internet access required  
✅ **Runtime**: CPU-only, AMD64 compatible  
✅ **Memory**: Operates within 16GB RAM limit  
✅ **Architecture**: Tested on AMD64 systems  

## Future Enhancements

Potential improvements for higher accuracy:
- Table of Contents parsing for better structure understanding
- Machine learning models for heading classification (within size limits)
- Advanced layout analysis for complex documents
- Improved multilingual pattern recognition