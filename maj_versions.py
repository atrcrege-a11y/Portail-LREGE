import re, json, sys

v = sys.argv[1]

# portail.py
with open('portail.py', encoding='utf-8') as f:
    c = f.read()
c = re.sub(r'VERSION_LOCALE = ["\']?[\d.]+["\']?', 'VERSION_LOCALE = "' + v + '"', c)
with open('portail.py', 'w', encoding='utf-8') as f:
    f.write(c)

# version.json
url = 'https://github.com/atrcrege-a11y/Portail-LREGE/releases/download/v' + v + '/PortailLREGE_Setup_v' + v + '.exe'
with open('version.json', 'w') as f:
    json.dump({'version': v, 'url': url}, f, indent=2)

# Vérification
with open('portail.py', encoding='utf-8') as f:
    check = f.read()
if 'VERSION_LOCALE = "' + v + '"' in check:
    print('OK')
else:
    print('ERREUR: VERSION_LOCALE mal ecrite')
    sys.exit(1)
