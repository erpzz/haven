"""Extract verified Linux runtimes without creating filesystem links."""
from pathlib import Path, PurePosixPath
import os
import shutil
import tarfile


def safe_extract_tar(archive: Path, target: Path, max_bytes: int = 3 * 1024 ** 3):
    """Materialize internal library aliases as regular files in a private stage.

    Official Linux releases contain relative .so aliases. Resolve those only
    against regular members of this archive, never against an external file.
    Reject special files, traversal, alias cycles and link-as-parent entries.
    """
    if target.is_symlink():
        raise ValueError('Runtime staging directory must not be a link.')
    target.mkdir(parents=True, exist_ok=True, mode=0o700)
    root = target.resolve()

    def relative(name):
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name:
            raise ValueError('Unsafe runtime archive path.')
        return path

    with tarfile.open(archive, 'r:gz') as source:
        members = {}
        for member in source.getmembers():
            name = relative(member.name)
            if name == PurePosixPath('.') and member.isdir():
                continue
            if not name.parts or not (member.isfile() or member.isdir() or member.issym() or member.islnk()):
                raise ValueError('Unsupported runtime archive member.')
            if name in members:
                raise ValueError('Duplicate runtime archive path.')
            members[name] = member

        def regular(name, seen=()):
            if name in seen or len(seen) >= 16 or name not in members:
                raise ValueError('Invalid runtime library alias.')
            member = members[name]
            if member.isfile():
                return member
            if member.issym() or member.islnk():
                link = relative(member.linkname)
                destination = name.parent / link if member.issym() else link
                return regular(destination, (*seen, name))
            raise ValueError('Runtime library alias must refer to a regular member.')

        expanded = 0
        for name, member in members.items():
            for parent in name.parents:
                if parent in members and not members[parent].isdir():
                    raise ValueError('Runtime archive uses a file or alias as a parent.')
            if not member.isdir():
                expanded += regular(name).size
        if expanded > max_bytes:
            raise ValueError('Runtime archive exceeds extraction limit.')

        for name, member in members.items():
            out = target.joinpath(*name.parts)
            for parent in (out, *out.parents):
                if parent == target.parent:
                    break
                if parent.is_symlink():
                    raise ValueError('Runtime extraction cannot traverse a link.')
            if not out.resolve().is_relative_to(root):
                raise ValueError('Runtime member escaped its stage.')
            if member.isdir():
                out.mkdir(parents=True, exist_ok=True, mode=0o700)
                continue
            out.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            if out.exists():
                raise ValueError('Runtime extraction would replace an existing file.')
            original = regular(name)
            stream = source.extractfile(original)
            if stream is None:
                raise ValueError('Runtime member has no readable content.')
            with stream, out.open('xb') as destination:
                shutil.copyfileobj(stream, destination, length=1024 ** 2)
            if out.stat().st_size != original.size:
                raise ValueError('Truncated runtime member.')
            os.chmod(out, 0o700 if original.mode & 0o111 else 0o600)
