import io
import re
import zipfile

def parse_markdown(text):
    metadata = {}
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.S)
    if match:
        for line in match.group(1).splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                metadata[key.strip()] = value.strip()
        text = match.group(2)
    return metadata, text

def load_zip(data):
    documents = []
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for name in z.namelist():
            if not name.lower().endswith('.md'):
                continue
            meta, text = parse_markdown(z.read(name).decode('utf-8'))
            documents.append({
                'file': name,
                'text': text,
                'source': meta.get('source', ''),
                'url': meta.get('url', ''),
                'published': meta.get('published', ''),
                'type': meta.get('type', ''),
            })
    return documents
