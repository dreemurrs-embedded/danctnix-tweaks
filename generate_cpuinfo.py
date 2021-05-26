import requests

response = requests.get('https://raw.githubusercontent.com/bp0/armids/master/arm.ids')
raw = response.content.decode()

current_implementer = None

implementers = {}
parts = {}

for line in raw.splitlines():
    if line.startswith('#'):
        continue
    if line.strip() == '':
        continue

    if line.startswith('\t'):
        code, name = line.split(' ', maxsplit=1)
        partid = int(code.strip(), 16)
        name = name.split('#')
        parts[current_implementer][partid] = name[0]
    else:
        code, name = line.split(' ', maxsplit=1)
        current_implementer = int(code.strip(), 16)
        implementers[current_implementer] = name.strip()
        parts[current_implementer] = {}

result = 'arm_implementer = {\n'

for implementer in implementers:
    result += f'    {implementer}: "{implementers[implementer]}",\n'
result += '}\n\narm_part = {\n'
for implementer in implementers:
    result += f'    {implementer}: ' + '{\n'
    for part in parts[implementer]:
        result += f'        {part}: "{parts[implementer][part]}",\n'
    result += '    },\n'
result += '}\n'

with open('pmos_tweaks/cpus.py', 'w') as handle:
    handle.write(result)
