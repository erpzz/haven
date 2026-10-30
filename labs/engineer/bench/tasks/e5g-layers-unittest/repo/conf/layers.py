from conf.merge import deep_merge

DEFAULTS = {"server": {"host": "127.0.0.1", "port": 8080}, "plugins": ["core"], "debug": False}


def load(*layers):
    cfg = DEFAULTS
    for layer in layers:
        cfg = deep_merge(cfg, layer)
    return cfg
