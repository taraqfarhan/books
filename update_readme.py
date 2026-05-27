#!/usr/bin/env python3
import os
import re
import datetime
import difflib

# Configuration
WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
README_PATH = os.path.join(WORKSPACE_DIR, 'README.md')

# Mapping from folder name to README section name
FOLDER_TO_SECTION = {
    'ai-ml': 'artificial intelligence',
    'operating-system': 'operating system',
    'self-help': 'self-help',
}

def dir_to_section(dir_name):
    return FOLDER_TO_SECTION.get(dir_name, dir_name.replace('-', ' '))

def normalize_text(text):
    if not text:
        return ""
    text = text.lower()
    text = text.replace('&', 'and')
    # Remove all non-alphanumeric characters
    return re.sub(r'[^a-z0-9]', '', text)

def books_match(pdf_title, pdf_author, entry_title, entry_author):
    # 1. Exact match of normalized strings (title + author combined)
    pdf_full = f"{pdf_title} - {pdf_author}" if pdf_author else pdf_title
    entry_full = f"{entry_title} - {entry_author}" if entry_author else entry_title
    
    pdf_norm = normalize_text(pdf_full)
    entry_norm = normalize_text(entry_full)
    
    if pdf_norm == entry_norm:
        return True
        
    # 2. Word set inclusion (handles extra words, subtitle differences, author order)
    pdf_words = set(re.findall(r'[a-z0-9]+', pdf_full.lower().replace('&', 'and')))
    entry_words = set(re.findall(r'[a-z0-9]+', entry_full.lower().replace('&', 'and')))
    
    if pdf_words.issubset(entry_words) or entry_words.issubset(pdf_words):
        intersection = pdf_words.intersection(entry_words)
        # Ensure they share a high percentage of words to prevent false matching short titles
        if len(intersection) >= min(len(pdf_words), len(entry_words)) * 0.8:
            return True
            
    # 3. Fuzzy similarity of full normalized strings
    ratio = difflib.SequenceMatcher(None, pdf_norm, entry_norm).ratio()
    if ratio >= 0.75:
        return True
        
    return False

def parse_readme_entry(line):
    # Regex to match "- [ ] content" or "- [x] content"
    entry_re = re.compile(r'^\s*-\s*\[([ x])\]\s*(.*)$')
    # Regex to match "**<ins>content</ins>**"
    reading_re = re.compile(r'^\*\*<ins>(.*)</ins>\*\*$')
    
    m = entry_re.match(line)
    if not m:
        return None
        
    checked = m.group(1) == 'x'
    content = m.group(2).strip()
    
    # Check if the content is wrapped in bold & underline (meaning currently reading)
    m_reading = reading_re.match(content)
    is_reading = False
    if m_reading:
        is_reading = True
        content = m_reading.group(1).strip()
        
    # Split Title and Author by " - " (split from right side to allow dashes in title)
    if ' - ' in content:
        title, author = content.rsplit(' - ', 1)
    else:
        title = content
        author = ""
        
    return {
        'title': title.strip(),
        'author': author.strip(),
        'checked': checked,
        'reading': is_reading
    }

def load_existing_books(readme_path):
    existing_books = {} # section_name -> list of book dicts
    if not os.path.exists(readme_path):
        return existing_books
        
    current_section = None
    section_re = re.compile(r'<summary><strong>(.*?)</strong>')
    
    with open(readme_path, 'r', encoding='utf-8') as f:
        for line in f:
            line_str = line.strip()
            # Detect section header
            sec_match = section_re.search(line_str)
            if sec_match:
                current_section = sec_match.group(1).strip()
                existing_books[current_section] = []
                continue
            
            # Detect end of section details block
            if '</details>' in line_str:
                current_section = None
                continue
                
            if current_section is not None:
                entry = parse_readme_entry(line)
                if entry:
                    existing_books[current_section].append(entry)
                    
    return existing_books

def parse_pdf_filename(filename):
    # Strip extension
    name = filename.rsplit('.', 1)[0]
    
    # Try parsing title and author using " by " or " By " or " BY "
    match = re.search(r'\s+by\s+', name, re.IGNORECASE)
    if match:
        title = name[:match.start()].strip()
        author = name[match.end():].strip()
    elif " - " in name:
        title, author = name.split(" - ", 1)
        title = title.strip()
        author = author.strip()
    else:
        title = name.strip()
        author = ""
        
    return title, author

def main():
    print("Scanning directories for books...")
    
    # 1. Parse existing README.md to preserve book status (checked, reading, original text styling)
    existing_books = load_existing_books(README_PATH)
    
    # 2. Scan filesystem for folders containing PDFs
    scanned_sections = {} # section_name -> list of book entries
    
    for item in sorted(os.listdir(WORKSPACE_DIR)):
        item_path = os.path.join(WORKSPACE_DIR, item)
        if os.path.isdir(item_path) and not item.startswith('.'):
            # Find all PDF files
            pdf_files = [f for f in os.listdir(item_path) if f.lower().endswith('.pdf')]
            if not pdf_files:
                continue
                
            section_name = dir_to_section(item)
            scanned_sections[section_name] = []
            
            # Get existing list of books for this section
            existing_list = existing_books.get(section_name, [])
            matched_indices = set()
            pdf_data = []
            
            for pdf_file in sorted(pdf_files):
                pdf_title, pdf_author = parse_pdf_filename(pdf_file)
                pdf_data.append({
                    'file': pdf_file,
                    'title': pdf_title,
                    'author': pdf_author,
                    'matched_entry': None
                })
                
            # Pass 1: Exact match of normalized strings
            for item_pdf in pdf_data:
                for idx, entry in enumerate(existing_list):
                    if idx in matched_indices:
                        continue
                    pdf_full = f"{item_pdf['title']} - {item_pdf['author']}" if item_pdf['author'] else item_pdf['title']
                    entry_full = f"{entry['title']} - {entry['author']}" if entry['author'] else entry['title']
                    if normalize_text(pdf_full) == normalize_text(entry_full):
                        item_pdf['matched_entry'] = entry
                        matched_indices.add(idx)
                        break
                        
            # Pass 2: Word set inclusion
            for item_pdf in pdf_data:
                if item_pdf['matched_entry']:
                    continue
                for idx, entry in enumerate(existing_list):
                    if idx in matched_indices:
                        continue
                    pdf_full = f"{item_pdf['title']} - {item_pdf['author']}" if item_pdf['author'] else item_pdf['title']
                    entry_full = f"{entry['title']} - {entry['author']}" if entry['author'] else entry['title']
                    
                    pdf_words = set(re.findall(r'[a-z0-9]+', pdf_full.lower().replace('&', 'and')))
                    entry_words = set(re.findall(r'[a-z0-9]+', entry_full.lower().replace('&', 'and')))
                    
                    if pdf_words.issubset(entry_words) or entry_words.issubset(pdf_words):
                        intersection = pdf_words.intersection(entry_words)
                        if len(intersection) >= min(len(pdf_words), len(entry_words)) * 0.8:
                            item_pdf['matched_entry'] = entry
                            matched_indices.add(idx)
                            break
                            
            # Pass 3: Fuzzy similarity
            for item_pdf in pdf_data:
                if item_pdf['matched_entry']:
                    continue
                best_idx = -1
                best_ratio = 0.0
                for idx, entry in enumerate(existing_list):
                    if idx in matched_indices:
                        continue
                    pdf_full = f"{item_pdf['title']} - {item_pdf['author']}" if item_pdf['author'] else item_pdf['title']
                    entry_full = f"{entry['title']} - {entry['author']}" if entry['author'] else entry['title']
                    
                    ratio = difflib.SequenceMatcher(None, normalize_text(pdf_full), normalize_text(entry_full)).ratio()
                    if ratio >= 0.75 and ratio > best_ratio:
                        best_ratio = ratio
                        best_idx = idx
                        
                if best_idx != -1:
                    item_pdf['matched_entry'] = existing_list[best_idx]
                    matched_indices.add(best_idx)
                    
            # Compile final entries
            for item_pdf in pdf_data:
                matched = item_pdf['matched_entry']
                if matched:
                    scanned_sections[section_name].append({
                        'title': matched['title'],
                        'author': matched['author'],
                        'checked': matched['checked'],
                        'reading': matched['reading']
                    })
                else:
                    print(f"New book detected in '{item}': {item_pdf['title']} (by {item_pdf['author'] if item_pdf['author'] else 'Unknown'})")
                    scanned_sections[section_name].append({
                        'title': item_pdf['title'],
                        'author': item_pdf['author'],
                        'checked': False,
                        'reading': False
                    })
                    
            # Sort the entries in each section alphabetically by title
            scanned_sections[section_name].sort(key=lambda x: x['title'].lower())

    # 3. Calculate statistics
    total_finished = 0
    total_reading = 0
    total_books = 0
    
    for section_name, books in scanned_sections.items():
        total_books += len(books)
        for book in books:
            if book['checked']:
                total_finished += 1
            elif book['reading']:
                total_reading += 1

    # 4. Generate README content
    now = datetime.datetime.now()
    last_updated_str = f"{now.day} {now.strftime('%B')}, {now.year}"
    
    sections_content = []
    # Sort section keys alphabetically
    for section_name in sorted(scanned_sections.keys()):
        books = scanned_sections[section_name]
        count = len(books)
        
        section_lines = [
            f"<details>",
            f"<summary><strong>{section_name}</strong> &nbsp;<code>{count}</code></summary>",
            f"<br>",
            ""
        ]
        
        for book in books:
            display_name = f"{book['title']} - {book['author']}" if book['author'] else book['title']
            if book['checked']:
                section_lines.append(f"- [x] {display_name}")
            elif book['reading']:
                section_lines.append(f"- [ ] **<ins>{display_name}</ins>**")
            else:
                section_lines.append(f"- [ ] {display_name}")
                
        section_lines.append("")
        section_lines.append("</details>")
        sections_content.append("\n".join(section_lines))
        
    sections_str = "\n\n".join(sections_content)
    
    new_readme = f"""# My Personal Book Collection

my personal collection of books across computer science, hacking, and beyond.

---

| finished | reading | total |
| :------: | :-----: | :---: |
|    {total_finished}    |    {total_reading}    |  {total_books}   |

---

## contents

{sections_str}

---

## key

- `[x]` → finished
- `[ ]` → **<ins>currently reading</ins>**
- `[ ]` → unread

---

## annotations in the books

I am using [Highlights](https://highlightsapp.net/) app to take notes in the books, and I have color coded the notes based on the following categories:

![Note Colors](image.png)

---

_last updated: {last_updated_str}_
"""

    with open(README_PATH, 'w', encoding='utf-8') as f:
        f.write(new_readme)
        
    print(f"README.md successfully updated! Total: {total_books} books ({total_finished} finished, {total_reading} reading).")

if __name__ == '__main__':
    main()
