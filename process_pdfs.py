import os
import json
import re
from pathlib import Path
import fitz  # PyMuPDF
from collections import defaultdict, Counter
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PDFOutlineExtractor:
    def __init__(self):
        # Common heading patterns
        self.heading_patterns = [
            # Numbered headings: 1., 1.1, 1.1.1, etc.
            r'^(\d+(?:\.\d+)*\.?)\s+(.+?)$',
            # Chapter/Section patterns
            r'^(Chapter\s+\d+|Section\s+\d+|Part\s+\d+)[:\.\s]+(.+?)$',
            # Roman numerals
            r'^([IVX]+)\.\s+(.+?)$',
            # Letter patterns: A., B., etc.
            r'^([A-Z])\.\s+(.+?)$',
            # Simple numbered: 1 Title, 2 Title
            r'^(\d+)\s+([A-Z].+?)$',
        ]
        
        # Title indicators
        self.title_keywords = [
            'title', 'document', 'report', 'manual', 'guide', 'handbook', 
            'specification', 'overview', 'analysis', 'study', 'research'
        ]
        
        # Words that indicate this is likely not a heading
        self.anti_heading_words = [
            'page', 'figure', 'table', 'image', 'note', 'see', 'refer', 
            'copyright', 'reserved', 'rights', 'published', 'printed'
        ]

    def extract_text_with_formatting(self, pdf_path):
        """Extract text with font size and style information"""
        doc = fitz.open(pdf_path)
        pages_data = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Get text blocks with font information
            blocks = page.get_text("dict")
            
            page_data = {
                'page_num': page_num + 1,  # 1-based page numbering to match test cases
                'lines': []
            }
            
            for block in blocks["blocks"]:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text = span["text"].strip()
                            if text:
                                page_data['lines'].append({
                                    'text': text,
                                    'font_size': span["size"],
                                    'font_flags': span["flags"],  # Bold, italic, etc.
                                    'font_name': span["font"],
                                    'bbox': span["bbox"]
                                })
            
            pages_data.append(page_data)
        
        doc.close()
        return pages_data

    def analyze_font_sizes(self, pages_data):
        """Analyze font sizes to determine heading levels"""
        font_sizes = []
        font_info = []
        
        for page in pages_data:
            for line in page['lines']:
                font_sizes.append(line['font_size'])
                font_info.append({
                    'size': line['font_size'],
                    'flags': line['font_flags'],
                    'text': line['text'],
                    'page': page['page_num']
                })
        
        if not font_sizes:
            return {}, []
        
        # Find common font sizes
        size_counter = Counter(font_sizes)
        sorted_sizes = sorted(size_counter.keys(), reverse=True)
        
        # Determine thresholds for different heading levels
        body_text_size = size_counter.most_common(1)[0][0]  # Most common size
        
        size_levels = {}
        level_counter = 1
        
        for size in sorted_sizes:
            if size > body_text_size and level_counter <= 3:
                if level_counter == 1:
                    size_levels[size] = 'H1'
                elif level_counter == 2:
                    size_levels[size] = 'H2'
                elif level_counter == 3:
                    size_levels[size] = 'H3'
                level_counter += 1
        
        return size_levels, font_info

    def is_likely_heading(self, text, font_size, font_flags, body_text_size):
        """Determine if text is likely a heading based on various criteria"""
        text = text.strip()
        
        # Skip very short text
        if len(text) < 3:
            return False
        
        # Skip text with anti-heading words
        text_lower = text.lower()
        if any(word in text_lower for word in self.anti_heading_words):
            return False
        
        # Check if it looks like a heading pattern
        for pattern in self.heading_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return True
        
        # Check font size (larger than body text)
        if font_size > body_text_size * 1.1:
            return True
        
        # Check if bold (font flags & 16 indicates bold)
        if font_flags & 16 and len(text) < 100:
            return True
        
        # Check if it's all caps and short
        if text.isupper() and len(text) < 50:
            return True
        
        # Check if it starts with capital and has specific patterns
        if (text[0].isupper() and 
            (text.endswith(':') or 
             re.match(r'^[A-Z][a-z].*[^.!?]$', text))):
            return True
        
        return False

    def determine_heading_level(self, text, font_size, size_levels):
        """Determine heading level based on font size and content"""
        # Pattern-based level detection (more precise for numbered sections)
        # Check for numbered patterns like "1.", "2.1", "2.1.1", etc.
        numbered_match = re.match(r'^(\d+(?:\.\d+)*)', text)
        if numbered_match:
            prefix = numbered_match.group(1)
            dot_count = prefix.count('.')
            
            if dot_count == 0:  # "1", "2", etc.
                return 'H1'
            elif dot_count == 1:  # "2.1", "3.2", etc.
                return 'H2'
            elif dot_count == 2:  # "2.1.1", "3.2.1", etc.
                return 'H3'
            else:  # "2.1.1.1" or more nested
                return 'H4' if dot_count == 3 else 'H3'
        
        # Check if font size matches predefined levels
        if font_size in size_levels:
            return size_levels[font_size]
        
        # General pattern-based detection
        for pattern in self.heading_patterns:
            match = re.match(pattern, text, re.IGNORECASE)
            if match:
                prefix = match.group(1)
                
                # Count dots to determine level
                if '.' in prefix:
                    dot_count = prefix.count('.')
                    if dot_count == 1:
                        return 'H1'
                    elif dot_count == 2:
                        return 'H2'
                    elif dot_count >= 3:
                        return 'H3'
                
                # Single number or letter = H1
                if re.match(r'^\d+$', prefix) or re.match(r'^[A-Z]$', prefix):
                    return 'H1'
        
        # Default based on relative font size
        return 'H1'  # Default to H1 if we can't determine

    def extract_title(self, pages_data):
        """Extract document title from the first few pages"""
        candidates = []
        
        # Look at first 3 pages for title candidates
        for page in pages_data[:3]:
            font_sizes = [line['font_size'] for line in page['lines'] if line['text'].strip()]
            if not font_sizes:
                continue
            
            max_font_size = max(font_sizes)
            
            for line in page['lines']:
                text = line['text'].strip()
                if (line['font_size'] >= max_font_size * 0.95 and  # Allow slight variation
                    len(text) > 3 and 
                    len(text) < 300 and  # Increased limit for longer titles
                    not any(word in text.lower() for word in self.anti_heading_words) and
                    not re.match(r'^\d+\.', text)):  # Skip numbered headings for title
                    
                    candidates.append({
                        'text': text,
                        'page': page['page_num'],
                        'font_size': line['font_size'],
                        'score': self.score_title_candidate(text)
                    })
        
        if candidates:
            # Sort by score and return best candidate
            candidates.sort(key=lambda x: x['score'], reverse=True)
            best_title = candidates[0]['text']
            
            # Some documents might have multiple title parts, try to combine them
            if len(candidates) > 1 and candidates[0]['page'] == candidates[1]['page']:
                # Check if second candidate is on same page and similar font size
                second = candidates[1]
                if (abs(candidates[0]['font_size'] - second['font_size']) < 2 and
                    not re.match(r'^\d+\.', second['text'])):
                    best_title = f"{best_title} {second['text']}"
            
            return best_title
        
        # Fallback: return first significant text
        for page in pages_data[:2]:
            for line in page['lines']:
                text = line['text'].strip()
                if (len(text) > 10 and 
                    not text.isdigit() and 
                    not re.match(r'^\d+\.', text)):
                    return text
        
        # Return empty string if no suitable title found (as in test cases 4 & 5)
        return ""

    def score_title_candidate(self, text):
        """Score title candidates based on various criteria"""
        score = 0
        text_lower = text.lower()
        
        # Prefer text with title keywords
        for keyword in self.title_keywords:
            if keyword in text_lower:
                score += 3
        
        # Prefer certain lengths
        if 10 <= len(text) <= 100:
            score += 2
        
        # Prefer text without numbers at the start
        if not re.match(r'^\d', text):
            score += 1
        
        # Prefer text that doesn't end with punctuation
        if not text.endswith(('.', '!', '?', ':')):
            score += 1
        
        return score

    def clean_heading_text(self, text):
        """Clean and normalize heading text"""
        # Keep the original text for numbered sections as they appear in test cases
        # Only clean if it's not a numbered section
        
        # Check if it's a numbered section (like "1. Introduction" or "2.1 Overview")
        if re.match(r'^\d+\.', text) or re.match(r'^\d+\.\d+', text):
            return text.strip()
        
        # For other patterns, try to extract meaningful part
        for pattern in self.heading_patterns:
            match = re.match(pattern, text, re.IGNORECASE)
            if match and len(match.groups()) >= 2:
                cleaned = match.group(2).strip()
                if cleaned:
                    return cleaned
        
        # Remove common prefixes only if no number prefix
        if not re.match(r'^\d+', text):
            text = re.sub(r'^(Chapter|Section|Part)\s+\d+[:\.\s]*', '', text, flags=re.IGNORECASE)
        
        return text.strip()

    def extract_outline(self, pdf_path):
        """Main method to extract outline from PDF"""
        try:
            logger.info(f"Processing {pdf_path}")
            
            # Extract text with formatting
            pages_data = self.extract_text_with_formatting(pdf_path)
            if not pages_data:
                logger.warning(f"No text found in {pdf_path}")
                return {"title": "Untitled Document", "outline": []}
            
            # Analyze font sizes
            size_levels, font_info = self.analyze_font_sizes(pages_data)
            
            # Find body text size for comparison
            font_sizes = [info['size'] for info in font_info]
            body_text_size = Counter(font_sizes).most_common(1)[0][0] if font_sizes else 12
            
            # Extract title
            title = self.extract_title(pages_data)
            
            # Extract headings
            outline = []
            seen_headings = set()  # To avoid duplicates
            
            for page in pages_data:
                for line in page['lines']:
                    text = line['text'].strip()
                    
                    if self.is_likely_heading(text, line['font_size'], line['font_flags'], body_text_size):
                        cleaned_text = self.clean_heading_text(text)
                        
                        # Avoid duplicates and very short headings
                        if cleaned_text and len(cleaned_text) > 2 and cleaned_text not in seen_headings:
                            level = self.determine_heading_level(text, line['font_size'], size_levels)
                            
                            outline.append({
                                "level": level,
                                "text": cleaned_text,
                                "page": page['page_num']
                            })
                            seen_headings.add(cleaned_text)
            
            # Sort outline by page number
            outline.sort(key=lambda x: x['page'])
            
            # Limit outline length for performance
            if len(outline) > 50:
                outline = outline[:50]
            
            result = {
                "title": title,
                "outline": outline
            }
            
            logger.info(f"Extracted {len(outline)} headings from {pdf_path}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing {pdf_path}: {str(e)}")
            return {"title": "Error Processing Document", "outline": []}

def process_pdfs():
    """Main function to process all PDFs in the input directory"""
    input_dir = Path("/app/input")
    output_dir = Path("/app/output")
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not input_dir.exists():
        logger.error(f"Input directory {input_dir} does not exist")
        return
    
    # Get all PDF files
    pdf_files = list(input_dir.glob("*.pdf"))
    
    if not pdf_files:
        logger.warning(f"No PDF files found in {input_dir}")
        return
    
    logger.info(f"Found {len(pdf_files)} PDF files to process")
    
    extractor = PDFOutlineExtractor()
    
    for pdf_file in pdf_files:
        try:
            # Extract outline
            result = extractor.extract_outline(pdf_file)
            
            # Create output JSON file
            output_file = output_dir / f"{pdf_file.stem}.json"
            
            with open(output_file, "w", encoding='utf-8') as f:
                json.dump(result, f, indent=4, ensure_ascii=False)
            
            logger.info(f"Processed {pdf_file.name} -> {output_file.name}")
            
        except Exception as e:
            logger.error(f"Failed to process {pdf_file.name}: {str(e)}")
            
            # Create empty result for failed files
            error_result = {"title": "Error Processing Document", "outline": []}
            output_file = output_dir / f"{pdf_file.stem}.json"
            
            with open(output_file, "w", encoding='utf-8') as f:
                json.dump(error_result, f, indent=4)

if __name__ == "__main__":
    logger.info("Starting PDF outline extraction")
    process_pdfs()
    logger.info("Completed PDF outline extraction")