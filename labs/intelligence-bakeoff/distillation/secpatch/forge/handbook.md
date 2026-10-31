You are writing training examples for a junior security reviewer. Your analysis will be shown to a model that
sees ONLY the code in the user's message — never the private notes, never any other version of the code.
Write what an expert reviewer would conclude from that code alone.

A strong analysis:
1. Names the function and the untrusted input (parameter, request field, file content, environment) and traces
   it to the sensitive operation (file open, SQL/shell/template/eval, redirect, deserialization, regex, network
   fetch, auth decision, allocation or loop bound).
2. States the exact missing or insufficient control (no normalization or containment check, no escaping, a
   comparison that can be bypassed, an unbounded size, a typo that disables a protection, a race window), citing
   it as "line N" with numbers from the gutter of the code shown.
3. Says concretely what an attacker gains, with a realistic malicious input when it helps
   (for example "a path such as ../../etc/passwd" or "a pattern of many repeated a characters").
4. For code that is safe, names the guard that makes it safe (normalization then containment check, an
   allow-list, escaping, a size limit, constant-time comparison) and why it is sufficient for this weakness.
5. Uses the CWE that matches the mechanism, not a generic one.

Hard rules:
- Mention only identifiers and line numbers that appear in the code shown.
- Never write "patch", "fix", "fixed version", "later", "reference", "advisory", "hint" or similar: the reader
  has no other version and no notes. Describe the weakness or the guard directly.
- Never describe history ("previously", "no longer", "now uses", "was missing"): the reader sees one version.
- Never guess ("likely", "probably", "appears to"). State what the code shown does; if a guard lives in a helper
  that is not shown, say only what the call site guarantees.
- Plain prose, no curly braces, no code blocks inside the analysis. Stay within the word limit.

Worked examples (synthetic code, showing the style):

Code shown (vulnerable): `  41 |     name = request.args["file"]` / `  42 |     return open(os.path.join(UPLOADS, name)).read()`
Analysis: read_upload takes the file query parameter on line 41 and joins it to UPLOADS on line 42 without
normalizing it or checking that the result stays inside UPLOADS. A request with file set to ../../etc/passwd, or
an absolute path, which os.path.join lets replace the base, reads any file the process can access. This is path
traversal (CWE-22).

Code shown (safe): `  41 |     path = os.path.realpath(os.path.join(UPLOADS, name))` /
`  42 |     if not path.startswith(os.path.realpath(UPLOADS) + os.sep): abort(403)`
Analysis: read_upload resolves the joined path with os.path.realpath on line 41, which collapses dot-dot segments
and symlinks, then on line 42 rejects any result outside the resolved UPLOADS directory, including the separator so
a sibling such as uploads-old cannot match. Traversal sequences and absolute paths are refused, so this code is not
vulnerable to path traversal.

Code shown (vulnerable): `  88 |     if token == settings.API_TOKEN:`
Analysis: check_token compares the caller's token with settings.API_TOKEN using == on line 88, which returns at
the first differing byte. Timing many requests lets an attacker recover the secret byte by byte. The comparison
should be constant-time; this is an observable timing discrepancy (CWE-208).

Code shown (vulnerable): `  12 |     m = re.match(r"^(\w+\s?)+$", title)`
Analysis: parse_title matches the caller's title against the pattern on line 12, whose group (\w+\s?) is repeated
by an outer + so the same characters can be split between iterations in exponentially many ways. A long run of word
characters ending in a character that cannot match, such as many a characters followed by an exclamation mark,
forces catastrophic backtracking and pins the CPU: regular-expression denial of service (CWE-1333, CWE-400). The
issue is the nested quantifier, not the characters the pattern allows.

Weakness playbook (what to look for, and what guard is actually sufficient):
- CWE-22/23/36 path traversal: user path joined to a base. Sufficient: resolve (realpath/resolve) then check
  containment against the resolved base plus separator; rejecting only ".." strings or using os.path.join alone
  is not (absolute paths, encoded or Windows separators, symlinks).
- CWE-78/77 command injection: shell=True, os.system or string-built commands with input. Sufficient: argument
  list without a shell. CWE-88 argument injection: input becomes an option (a value starting with "-" passed to
  git, ssh, tar, curl); sufficient: an end-of-options "--" before user values, or rejecting a leading "-". A list
  of arguments alone does NOT stop option injection.
- CWE-94/95 code injection: eval, exec, compile, template rendering of user text, pickle-like loaders.
  Sufficient: no evaluation of input; ast.literal_eval for literals; sandboxed templates.
- CWE-502 deserialization: pickle, yaml.load without SafeLoader, torch.load without weights_only, jsonpickle on
  untrusted data. Sufficient: a safe loader or a data-only format.
- CWE-79 XSS: input reaching HTML without escaping (mark_safe, |safe, Markup, innerHTML, format_html misuse).
  Sufficient: contextual auto-escaping, escape() at the sink, sanitizers with allow-lists.
- CWE-89 SQL injection: string formatting into SQL. Sufficient: bound parameters; identifiers from an allow-list.
- CWE-918 SSRF: server fetches a user URL. Sufficient: scheme allow-list plus resolving the host and rejecting
  private, loopback and link-local addresses at connect time (redirects re-checked).
- CWE-601 open redirect: redirect target from input. Sufficient: relative-path-only or host allow-list after
  parsing; watch for "//evil.com", backslashes and scheme-relative URLs.
- CWE-400/770/1333/834 resource exhaustion: unbounded sizes, loops, recursion, decompression, or regexes with
  nested quantifiers (catastrophic backtracking). Sufficient: explicit limits, linear-time patterns, timeouts.
- CWE-287/306/862/863/285 authentication and authorization: missing or bypassable checks, wrong object owner
  checks, default-allow branches. Sufficient: the check on every path before the action.
- CWE-347/295/327 crypto and signatures: verification disabled (verify=False), signatures not checked, algorithm
  "none" accepted, weak algorithms. Sufficient: verification enforced with pinned algorithms.
- CWE-208 timing: == on secrets. Sufficient: hmac.compare_digest or secrets.compare_digest.
- CWE-200/532/209 exposure: secrets or internals in responses, logs or errors. Sufficient: redaction, generic
  errors.
- CWE-352 CSRF: state-changing endpoint without a token or with exemptions. CWE-611 XXE: XML parser resolving
  external entities. CWE-362/367 races: check-then-use on files or state without atomicity.
- CWE-20 improper validation: name the specific missing validation and what it lets through, rather than
  stopping at "input is not validated".
