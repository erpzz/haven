"""Read package license declarations as data; never execute project code."""
import ast
import configparser
import pathlib
import re
import tomllib

def declarations(path, raw):
 text=raw.decode('utf8','replace'); out=[]
 if path.endswith('pyproject.toml'):
  try: d=tomllib.loads(text)
  except tomllib.TOMLDecodeError as exc: raise ValueError('Malformed package metadata: ' + path) from exc
  for group in [d.get('project',{}), d.get('tool',{}).get('poetry',{})]:
   lic=group.get('license')
   if isinstance(lic,str):out.append(lic)
   elif isinstance(lic,dict):
    if lic.get('text'):out.append(lic['text'])
    elif lic.get('file'):out.append('FILE:'+lic['file'])
   out += [x for x in group.get('classifiers',[]) if x.startswith('License ::')]
 elif path.endswith('setup.cfg'):
  c=configparser.ConfigParser(interpolation=None,strict=False)
  try:c.read_string(text)
  except configparser.Error as exc:raise ValueError('Malformed package metadata: ' + path) from exc
  if c.has_section('metadata'):
   if c.has_option('metadata','license'):out.append(c.get('metadata','license'))
   out += [x.strip() for x in c.get('metadata','classifiers',fallback='').splitlines() if x.strip().startswith('License ::')]
 elif path.endswith('setup.py'):
  try:t=ast.parse(text)
  except SyntaxError as exc:raise ValueError('Malformed package metadata: ' + path) from exc
  vars={}
  for node in t.body:
   if isinstance(node,ast.Assign):
    try:v=ast.literal_eval(node.value)
    except (ValueError,TypeError):continue
    for target in node.targets:
     if isinstance(target,ast.Name):vars[target.id]=v
  for node in ast.walk(t):
   if isinstance(node,ast.Call) and ((isinstance(node.func,ast.Name) and node.func.id=='setup') or (isinstance(node.func,ast.Attribute) and node.func.attr=='setup')):
    for kw in node.keywords:
     if kw.arg=='license':
      try:v=vars[kw.value.id] if isinstance(kw.value,ast.Name) else ast.literal_eval(kw.value)
      except (KeyError,ValueError,TypeError):v='DYNAMIC'
      if isinstance(v,str):out.append(v)
   if isinstance(node,ast.Constant) and isinstance(node.value,str) and node.value.startswith('License ::'):out.append(node.value)
 elif path.endswith('PKG-INFO'):
  out += [l.split(':',1)[1].strip() for l in text.splitlines() if l.startswith(('License:','Classifier: License ::'))]
 return list(dict.fromkeys(out))



def _allowed_atom(value):
    """Conservatively classify one license grant, not an SPDX expression."""
    v = value.lower().strip()
    if not v or v in ('dynamic', 'unknown', 'license :: osi approved') or v.startswith('file:'):
        return False
    if v.startswith('license :: osi approved :: '):
        v = v[len('license :: osi approved :: '):]
    if re.fullmatch(r'(?:a?gpl|lgpl)(?:[- ]\d+(?:\.\d+)?(?:-or-later|-only)?)?', v) or \
            re.fullmatch(r'(?:fsl-[a-z0-9.\-]+|zpl(?: \d+(?:\.\d+)?)?|proprietary|mpl-\d+(?:\.\d+)?)', v):
        return False
    allowed = bool(re.fullmatch(
        r'(?:mit(?: license)?|apache(?:[- ](?:2\.0|license(?:,? version)? 2\.0|software license(?: 2\.0)?))?'
        r'|asl 2(?:\.0)?|bsd(?:[- ](?:2|3)[- ]clause(?: license)?| license)?'
        r'|isc(?: license)?|psf(?: license)?|python software foundation(?: license)?'
        r'|unlicense|0bsd)', v))
    if not allowed:
        raise ValueError('Unrecognized license atom')
    return True


def allowed_declaration(value):
    """SPDX AND/OR precedence; reject malformed/unknown expressions closed."""
    if not isinstance(value, str):
        return False
    tokens = re.findall(r'\(|\)|\bAND\b|\bOR\b|[^\s()]+', value, flags=re.I)
    if not tokens:
        return False
    # License names can contain spaces. Operators and parentheses delimit operands.
    pos = 0

    def atom():
        nonlocal pos
        if pos < len(tokens) and tokens[pos] == '(':
            pos += 1
            result = disjunction()
            if pos >= len(tokens) or tokens[pos] != ')':
                raise ValueError('unclosed SPDX expression')
            pos += 1
            return result
        start = pos
        while pos < len(tokens) and tokens[pos].upper() not in ('AND', 'OR') and tokens[pos] not in ('(', ')'):
            pos += 1
        if start == pos:
            raise ValueError('missing license operand')
        return _allowed_atom(' '.join(tokens[start:pos]))

    def conjunction():
        nonlocal pos
        result = atom()
        while pos < len(tokens) and tokens[pos].upper() == 'AND':
            pos += 1
            rhs = atom()  # Parse RHS even when the left is false.
            result = result and rhs
        return result

    def disjunction():
        nonlocal pos
        result = conjunction()
        while pos < len(tokens) and tokens[pos].upper() == 'OR':
            pos += 1
            rhs = conjunction()
            result = result or rhs
        return result

    try:
        result = disjunction()
        return result if pos == len(tokens) else False
    except ValueError:
        return False


def _applies_to_source(path, source):
    p = pathlib.PurePosixPath(path)
    if not path or p.is_absolute() or '..' in p.parts or p.name in ('', '.', '..'):
        raise ValueError('Invalid source audit path')
    parent = p.parent
    return parent == pathlib.PurePosixPath('.') or parent in source.parents


def validate_metadata(item, contents):
    """Nearest applicable package metadata; deeper source license can override."""
    source_name = item.get('source_path')
    if not isinstance(source_name, str) or not source_name:
        raise ValueError('Missing audited source path: ' + str(item.get('key')))
    source = pathlib.PurePosixPath(source_name)
    if source.is_absolute() or '..' in source.parts or source.name in ('', '.', '..'):
        raise ValueError('Invalid audited source path: ' + str(item.get('key')))
    notice_paths = {n['path'] for n in item['notices']}
    license_depth = max((p.count('/') for p in notice_paths if re.search(
        r'(?:^|/)(?:LICEN[CS]E|COPYING)(?:\.(?:md|txt|rst))?$', p, re.I)
        and _applies_to_source(p, source)), default=-1)
    declarations_by_path = []
    for entry in item.get('metadata', []):
        path = entry['path']
        if not _applies_to_source(path, source):
            raise ValueError('Package metadata is not on the source path: ' + item['key'])
        values = declarations(path, contents[entry['sha256']])
        if values:
            declarations_by_path.append((path, values))
    depth = max((p.count('/') for p, _ in declarations_by_path), default=-1)
    effective = [(p, values) for p, values in declarations_by_path if p.count('/') == depth]
    if depth < license_depth:
        return {'precedence': 'deeper_source_license', 'metadata': effective}
    if depth < 0 and license_depth < 0:
        raise ValueError('No applicable source license or package declaration: ' + item['key'])
    for path, values in effective:
        for value in values:
            if value.startswith('FILE:'):
                ref = str(pathlib.PurePosixPath(path).parent / value[5:])
                if ref not in notice_paths or not _applies_to_source(ref, source):
                    raise ValueError('Package metadata references an unretained license: ' + item['key'])
            elif not allowed_declaration(value):
                raise ValueError('Package metadata license is outside campaign allowlist: ' + item['key'])
    return {'precedence': 'nearest_package_metadata_and_source_notices', 'metadata': effective}
