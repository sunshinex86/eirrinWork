import re

with open('fetched_content.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Find article content
start = html.find('<article class="md-content__inner md-typeset">')
end = html.find('</article>', start)

if start != -1 and end != -1:
    article = html[start:end+10]
    # Extract text content by removing tags
    text = re.sub(r'<[^>]+>', '', article)
    # Clean up whitespace
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    content = '\n\n'.join(lines)
    
    with open('guides.md', 'w', encoding='utf-8') as f:
        f.write('# Installing and managing Python\n\n')
        f.write('Source: https://docs.astral.sh/uv/guides/install-python/\n\n')
        f.write('---\n\n')
        f.write(content[:8000])
    print('Saved guides.md, length:', len(content))
else:
    print('Article not found')