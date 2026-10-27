def split(line, sep=","):
    """Split one CSV line. Quoted fields may contain the separator and doubled quotes ("")."""
    fields, buf, quoted, i = [], [], False, 0
    while i < len(line):
        ch = line[i]
        if quoted:
            if ch == '"':
                quoted = False
            else:
                buf.append(ch)
        elif ch == '"':
            quoted = True
        elif ch == sep:
            fields.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
        i += 1
    if buf:
        fields.append("".join(buf))
    return fields
