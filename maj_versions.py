import re, json, sys

v = sys.argv[1]

# portail.py
c = open('portail.py', encoding='utf-8').read()
c = re.sub(r'VERSION_LOCALE = "[^"]*"', 'VERSION_LOCALE = "' + v + '"', c)
open('portail.py', 'w', encoding='utf-8').write(c)

# setup.iss
c = open('setup.iss', encoding='utf-8').read()
c = re.sub(r'#define AppVersion "[^"]*"', '#define AppVersion "' + v + '"', c)
open('setup.iss', 'w', encoding='utf-8').write(c)

# version.json
url = 'https://github.com/atrcrege-a11y/Portail-LREGE/releases/download/v' + v + '/PortailLREGE_Setup_v' + v + '.exe'
json.dump({'version': v, 'url': url}, open('version.json', 'w'), indent=2)

print('OK')
