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
  except tomllib.TOMLDecodeError: return []
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
  except configparser.Error:return []
  if c.has_section('metadata'):
   if c.has_option('metadata','license'):out.append(c.get('metadata','license'))
   out += [x.strip() for x in c.get('metadata','classifiers',fallback='').splitlines() if x.strip().startswith('License ::')]
 elif path.endswith('setup.py'):
  try:t=ast.parse(text)
  except SyntaxError:return []
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


def allowed_declaration(value):
    """The existing campaign allowlist, including explicit permitted alternatives."""
    v = value.lower().strip()
    if v in ('dynamic', 'license :: osi approved', 'unknown', '') or v.startswith('file:'):
        return True  # A file reference is checked against retained notices below.
    if any(x in v for x in ('fsl-', 'proprietary', 'zope public', 'zpl', 'repoze', 'mozilla', 'mpl-')):
        return False
    allowed = bool(re.search(r'\b(?:mit|apache\w*|asl 2|bsd\w*|isc|psf|python software foundation|unlicense|0bsd)\b', v))
    if 'gpl' in v or 'general public license' in v:
        return allowed and (' or ' in v)  # e.g. Apache OR GPL; choose the allowed grant.
    return allowed


def validate_metadata(item, contents):
    """Nearest package metadata applies unless a deeper source license overrides it."""
    notice_paths = {n['path'] for n in item['notices']}
    license_depth = max((p.count('/') for p in notice_paths if re.search(
        r'(?:^|/)(?:LICEN[CS]E|COPYING)(?:\.(?:md|txt|rst))?$', p, re.I)), default=0)
    declarations_by_path = []
    for entry in item.get('metadata', []):
        values = declarations(entry['path'], contents[entry['sha256']])
        if values:
            declarations_by_path.append((entry['path'], values))
    depth = max((p.count('/') for p, _ in declarations_by_path), default=-1)
    effective = [(p, values) for p, values in declarations_by_path if p.count('/') == depth]
    if depth < license_depth:
        return {'precedence': 'deeper_source_license', 'metadata': effective}
    for path, values in effective:
        for value in values:
            if value.startswith('FILE:'):
                ref = str(pathlib.PurePosixPath(path).parent / value[5:])
                if ref not in notice_paths:
                    raise ValueError('Package metadata references an unretained license: ' + item['key'])
            elif not allowed_declaration(value):
                raise ValueError('Package metadata license is outside campaign allowlist: ' + item['key'])
    return {'precedence': 'nearest_package_metadata_and_source_notices', 'metadata': effective}
