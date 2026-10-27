def parse_bool(value):
    return {'true': True, 'false': False}[value]


def load(lines):
    out = {}
    for line in lines:
        if not line.strip() or line.startswith('#'):
            continue
        key, value = line.split('=', 1)
        out[key.strip()] = value.strip()
    return out
