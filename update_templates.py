import os
import glob

template_dir = 'templates'
files = glob.glob(os.path.join(template_dir, '*.html'))

link_tag = '<link rel="stylesheet" href="{{ url_for(\'static\', filename=\'css/global.css\') }}">\n</head>'
divs = '<body>\n\n<div class="ambient-glow"></div>\n<div class="ambient-glow-2"></div>'

for filepath in files:
    if os.path.basename(filepath) == 'index.html':
        continue
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    updated = False
    if 'global.css' not in content and '</head>' in content:
        content = content.replace('</head>', link_tag)
        updated = True
        
    if '<div class="ambient-glow"></div>' not in content and '<body>' in content:
        content = content.replace('<body>', divs)
        updated = True
        
    if updated:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'Updated {os.path.basename(filepath)}')
