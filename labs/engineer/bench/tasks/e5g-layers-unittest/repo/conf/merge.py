def deep_merge(base, override):
    """Return base updated by override. Nested dicts merge; any other value (lists too) replaces. Inputs are not modified."""
    out = base
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        elif isinstance(v, list) and isinstance(out.get(k), list):
            out[k] = out[k] + v
        else:
            out[k] = v
    return out
