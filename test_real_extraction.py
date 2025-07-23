#!/usr/bin/env python3
"""
Test real extraction algorithm against sample PDFs
"""

import json
from pathlib import Path
from process_pdfs import ExactMatchPDFExtractor

def test_real_extraction():
    """Test our real extraction algorithm"""
    
    # Test on sample PDFs
    pdfs_dir = Path("test_real/Challenge_1a/sample_dataset/pdfs")
    extractor = ExactMatchPDFExtractor()
    
    for pdf_file in pdfs_dir.glob("*.pdf"):
        print(f"\n📄 Processing {pdf_file.name}...")
        
        result = extractor.extract_outline(pdf_file)
        
        print(f"Title: '{result['title']}'")
        print(f"Outline: {len(result['outline'])} headings")
        
        for i, heading in enumerate(result['outline'][:10]):  # Show first 10
            print(f"  {i+1}. {heading['level']} '{heading['text']}' page {heading['page']}")
        
        if len(result['outline']) > 10:
            print(f"  ... and {len(result['outline']) - 10} more")
        
        # Save to file for inspection
        output_file = f"output_{pdf_file.stem}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"Saved to {output_file}")

if __name__ == "__main__":
    test_real_extraction()