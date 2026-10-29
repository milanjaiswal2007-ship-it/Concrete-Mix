import os
import pypdf
import re
from collections import Counter

folders = [
    r"c:\Users\Prakash\OneDrive\Desktop\paper 1 references",
    r"c:\Users\Prakash\OneDrive\Desktop\paper 2 references"
]

all_files = []
for folder in folders:
    for f in os.listdir(folder):
        if f.lower().endswith('.pdf'):
            all_files.append((folder, f, os.path.join(folder, f)))

print(f"Total PDFs found: {len(all_files)}")

# Deduplicate by filename
unique_files = {}
for folder, fname, fpath in all_files:
    if fname not in unique_files:
        unique_files[fname] = fpath

print(f"Unique PDFs: {len(unique_files)}")

# Extract metadata & title/topics
topics = Counter()
materials = Counter()
activators = Counter()
curings = Counter()

keywords_to_check = {
    "materials": ["fly ash", "ggbs", "slag", "metakaolin", "silica fume", "rice husk ash", "rha", "red mud", "palm oil fuel ash", "pofa", "nano silica", "recycled aggregate", "m-sand", "manufactured sand"],
    "activators": ["sodium hydroxide", "naoh", "sodium silicate", "na2sio3", "potassium hydroxide", "koh", "potassium silicate", "k2sio3", "one-part", "one part", "solid activator", "molarity", "modulus"],
    "curing": ["ambient", "heat cured", "oven cured", "elevated temperature", "steam curing", "room temperature", "water curing", "membrane curing"],
    "fibers": ["steel fiber", "steel fibre", "pp fiber", "polypropylene", "pva fiber", "basalt fiber", "carbon fiber"],
    "durability": ["acid resistance", "sulphate", "sulfate", "carbonation", "chloride", "fire", "elevated temperature", "thermal", "shrinkage", "creep"]
}

category_counts = {cat: Counter() for cat in keywords_to_check}
paper_summaries = []

for idx, (fname, fpath) in enumerate(unique_files.items()):
    try:
        reader = pypdf.PdfReader(fpath)
        num_pages = len(reader.pages)
        first_page_text = reader.pages[0].extract_text() or ""
        
        # Check first 3 pages
        sample_text = ""
        for p in range(min(3, num_pages)):
            sample_text += " " + (reader.pages[p].extract_text() or "")
        sample_text_lower = sample_text.lower()
        
        # Extract title (usually first few lines of page 1)
        lines = [l.strip() for l in first_page_text.split('\n') if len(l.strip()) > 10]
        title_guess = lines[0] if lines else fname
        
        for cat, kws in keywords_to_check.items():
            for kw in kws:
                if kw in sample_text_lower:
                    category_counts[cat][kw] += 1
                    
        paper_summaries.append({
            "filename": fname,
            "pages": num_pages,
            "title_guess": title_guess[:120]
        })
    except Exception as e:
        # print error
        pass

print("\n--- MATERIALS DETECTED ---")
for kw, count in category_counts["materials"].most_common(15):
    print(f"  {kw}: {count} papers")

print("\n--- ACTIVATORS DETECTED ---")
for kw, count in category_counts["activators"].most_common(15):
    print(f"  {kw}: {count} papers")

print("\n--- CURING REGIMES DETECTED ---")
for kw, count in category_counts["curing"].most_common(15):
    print(f"  {kw}: {count} papers")

print("\n--- FIBERS DETECTED ---")
for kw, count in category_counts["fibers"].most_common(10):
    print(f"  {kw}: {count} papers")

print("\n--- DURABILITY / PERFORMANCE DETECTED ---")
for kw, count in category_counts["durability"].most_common(10):
    print(f"  {kw}: {count} papers")
