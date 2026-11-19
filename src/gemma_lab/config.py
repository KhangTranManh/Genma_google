from dataclasses import dataclass
from pathlib import Path
import tomllib

@dataclass(frozen=True)
class Project:
    root: Path
    raw: dict

    def path(self, name):
        return (self.root / self.raw["paths"][name]).resolve()

    def select(self, kind, key=None):
        key = key or self.raw["defaults"][kind]
        group = self.raw[kind + "s"]
        if key not in group:
            raise ValueError(f"Unknown {kind}: {key}. Choose: {', '.join(group)}")
        return key, group[key]

def merge(base, override):
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge(result[key], value)
        else:
            result[key] = value
    return result

def load(path, _seen=None):
    path = Path(path).resolve()
    seen = set() if _seen is None else set(_seen)
    if path in seen:
        raise ValueError("Cyclic config inheritance")
    seen.add(path)
    with path.open("rb") as stream:
        raw = tomllib.load(stream)
    parent = raw.pop("extends", None)
    if parent:
        inherited = load(path.parent / parent, seen)
        return Project(inherited.root, merge(inherited.raw, raw))
    return Project(path.parent.parent, raw)
