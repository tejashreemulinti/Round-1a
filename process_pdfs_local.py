import os
import json
import re
from pathlib import Path
import fitz  # PyMuPDF
from collections import defaultdict, Counter
import logging
import tempfile

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
                'page_num': page_num,
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
        # First check if font size matches predefined levels
        if font_size in size_levels:
            return size_levels[font_size]
        
        # Pattern-based level detection
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
                if (line['font_size'] == max_font_size and 
                    len(text) > 5 and 
                    len(text) < 200 and
                    not any(word in text.lower() for word in self.anti_heading_words)):
                    
                    candidates.append({
                        'text': text,
                        'page': page['page_num'],
                        'font_size': line['font_size'],
                        'score': self.score_title_candidate(text)
                    })
        
        if candidates:
            # Sort by score and return best candidate
            candidates.sort(key=lambda x: x['score'], reverse=True)
            return candidates[0]['text']
        
        # Fallback: return first significant text
        for page in pages_data[:2]:
            for line in page['lines']:
                text = line['text'].strip()
                if len(text) > 10 and not text.isdigit():
                    return text
        
        return "Untitled Document"

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
        # Remove numbering prefix but keep the meaningful part
        for pattern in self.heading_patterns:
            match = re.match(pattern, text, re.IGNORECASE)
            if match and len(match.groups()) >= 2:
                cleaned = match.group(2).strip()
                if cleaned:
                    return cleaned
        
        # Remove common prefixes
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

def get_safe_directory(folder_name):
    """Get a safe directory path that we can write to on Windows"""
    # Try user's Documents folder first
    try:
        documents_path = Path.home() / "Documents" / "PDF_Extractor" / folder_name
        documents_path.mkdir(parents=True, exist_ok=True)
        # Test if we can write to it
        test_file = documents_path / "test_write.tmp"
        test_file.write_text("test")
        test_file.unlink()
        return documents_path
    except (PermissionError, OSError):
        pass
    
    # Try Desktop
    try:
        desktop_path = Path.home() / "Desktop" / "PDF_Extractor" / folder_name
        desktop_path.mkdir(parents=True, exist_ok=True)
        test_file = desktop_path / "test_write.tmp"
        test_file.write_text("test")
        test_file.unlink()
        return desktop_path
    except (PermissionError, OSError):
        pass
    
    # Try current directory
    try:
        current_dir = Path.cwd()
        target_dir = current_dir / folder_name
        target_dir.mkdir(parents=True, exist_ok=True)
        test_file = target_dir / "test_write.tmp"
        test_file.write_text("test")
        test_file.unlink()
        return target_dir
    except (PermissionError, OSError):
        pass
    
    # Try temp directory as last resort
    try:
        import tempfile
        temp_dir = Path(tempfile.gettempdir()) / "PDF_Extractor" / folder_name
        temp_dir.mkdir(parents=True, exist_ok=True)
        return temp_dir
    except (PermissionError, OSError):
        pass
    
    # If all else fails, return None
    return None

def process_pdfs_local(input_folder="input", output_folder="output"):
    """Process PDFs from local folders with Windows permission handling"""
    print("🚀 PDF Outline Extractor - Local Version")
    print("=" * 50)
    
    # Try to get safe directories
    print("📁 Setting up directories...")
    
    input_dir = get_safe_directory(input_folder)
    output_dir = get_safe_directory(output_folder)
    
    if input_dir is None or output_dir is None:
        print("❌ Cannot create directories due to permission issues.")
        print("\n🔧 Solutions:")
        print("1. Run as Administrator")
        print("2. Move the script to a folder you have write access to (like Desktop)")
        print("3. Use a different folder location")
        return False
    
    print(f"✅ Input directory: {input_dir}")
    print(f"✅ Output directory: {output_dir}")
    
    if not input_dir.exists():
        print(f"📁 Created input directory: {input_dir}")
        input_dir.mkdir(parents=True, exist_ok=True)
    
    # Get all PDF files
    pdf_files = list(input_dir.glob("*.pdf"))
    
    if not pdf_files:
        print(f"\n⚠️  No PDF files found in: {input_dir}")
        print(f"\n📝 Next steps:")
        print(f"1. Copy your PDF files to: {input_dir}")
        print(f"2. Run this script again")
        print(f"\n💡 You can also drag & drop PDF files into that folder!")
        return False
    
    logger.info(f"Found {len(pdf_files)} PDF files to process")
    print(f"📄 Found {len(pdf_files)} PDF files to process...")
    
    extractor = PDFOutlineExtractor()
    
    success_count = 0
    for pdf_file in pdf_files:
        try:
            print(f"\n🔄 Processing: {pdf_file.name}")
            
            # Extract outline
            result = extractor.extract_outline(pdf_file)
            
            # Create output JSON file
            output_file = output_dir / f"{pdf_file.stem}.json"
            
            with open(output_file, "w", encoding='utf-8') as f:
                json.dump(result, f, indent=4, ensure_ascii=False)
            
            logger.info(f"Processed {pdf_file.name} -> {output_file.name}")
            print(f"✅ Generated: {output_file.name}")
            print(f"   📊 Found {len(result['outline'])} headings")
            print(f"   📝 Title: {result['title'][:50]}{'...' if len(result['title']) > 50 else ''}")
            
            success_count += 1
            
        except Exception as e:
            logger.error(f"Failed to process {pdf_file.name}: {str(e)}")
            print(f"❌ Failed to process: {pdf_file.name}")
            print(f"   Error: {str(e)}")
            
            # Create empty result for failed files
            try:
                error_result = {"title": "Error Processing Document", "outline": []}
                output_file = output_dir / f"{pdf_file.stem}.json"
                
                with open(output_file, "w", encoding='utf-8') as f:
                    json.dump(error_result, f, indent=4)
                print(f"   💾 Created error placeholder: {output_file.name}")
            except Exception:
                print(f"   ⚠️  Could not create error file")
    
    print(f"\n✨ Processing complete!")
    print(f"📊 Successfully processed: {success_count}/{len(pdf_files)} files")
    print(f"📁 Results saved to: {output_dir}")
    
    return True

if __name__ == "__main__":
    logger.info("Starting PDF outline extraction (local mode)")
    success = process_pdfs_local("input", "output")
    
    if success:
        print("\n🎉 All done! Check the output folder for your JSON files.")
    else:
        print("\n⚠️  Process completed with issues. See messages above.")
    
    # Keep window open on Windows
    input("\nPress Enter to exit...")
    
    logger.info("Completed PDF outline extraction")