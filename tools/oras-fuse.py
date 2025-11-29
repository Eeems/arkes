#!/usr/bin/env python3
import os
import sys
import time
import threading
import errno
import tarfile
import io
import tempfile
import fuse
import oras.client

import zstandard as zstd

fuse.fuse_python_api = (0, 2)


class Stat(fuse.Stat):
    def __init__(self):
        self.st_mode = 0
        self.st_ino = 0
        self.st_dev = 0
        self.st_nlink = 0
        self.st_uid = 0
        self.st_gid = 0
        self.st_size = 0
        self.st_atime = 0
        self.st_mtime = 0
        self.st_ctime = 0


# ----------------------------------------------------------------------
# Hot-reloading ORAS FUSE implementation
# ----------------------------------------------------------------------
class HotReloadORASFuse(fuse.Fuse):
    def __init__(
        self,
        target: str,
        mountpoint: str,
        username=None,
        password=None,
        token=None,
        insecure=False,
        reload_interval=30,
        *args,
        **kwds,
    ):
        self.client = oras.client.OrasClient(insecure=insecure)
        self.target = target
        self.reload_interval = reload_interval

        # === Authentication ===
        if token:
            # For token auth (e.g., GHCR PAT), use username="dummy" and password=token
            self.client.login(username="dummy", password=token)
        elif username and password:
            self.client.login(username=username, password=password)

        self._tree_lock = threading.RLock()
        self.current_tree = None

        # Load first version
        self._load_new_tree()

        # Background reloader
        threading.Thread(target=self._reloader, daemon=True).start()
        fuse.Fuse.__init__(self, *args, **kwds)
        self.fuse_args.mountpoint = mountpoint
        self.fuse_args.add("use_ino")
        self.fuse_args.add("kernel_cache")
        self.fuse_args.add("nonempty")
        self.fuse_args.add("default_permissions")
        self.fuse_args.add("attr_timeout=1.0")
        self.fuse_args.add("entry_timeout=1.0")
        self.fuse_args.add("negative_timeout=0")
        self.multithreaded = False

    def _load_new_tree(self):
        print(f"[{time.strftime('%H:%M:%S')}] Pulling {self.target} ...")
        manifest = self.client.get_manifest(self.target)
        layers = manifest.get("layers", [])
        if not layers:
            raise RuntimeError("No layers in manifest")

        tree = {
            "/": {
                "type": "dir",
                "children": {},
                "mode": 0o40755,
                "size": 4096,
                "mtime": time.time(),
            }
        }

        for idx, layer in enumerate(layers):
            digest = layer["digest"]
            media_type = layer.get("mediaType", "")
            annotations = layer.get("annotations", {})

            print(f"  → layer {digest[:12]}  ({media_type})")

            # 1. Skip estargz layers
            if "estargz" in media_type.lower():
                print("     ↳ estargz – skipping")
                continue

            # 2. Download the blob
            with tempfile.NamedTemporaryFile() as tmpfile:
                self.client.download_blob(self.target, digest, outfile=tmpfile.name)
                tmpfile.seek(0)
                data = tmpfile.read()

            # 3. Decide how to interpret it
            is_tar_layer = (
                media_type.endswith(".tar")
                or media_type.endswith("+gzip")
                or media_type.endswith("+zstd")
                or "tar" in media_type.lower()
            )

            if not is_tar_layer and len(layers) == 1:
                # Heuristic: single non-tar layer → treat as raw file
                filename = annotations.get(
                    "org.opencontainers.image.title",  # standard
                    f"layer-{idx}-{digest[:12]}",
                )
                path = "/" + filename
                print(f"     ↳ single-file artifact → {path}")

                tree[path] = {
                    "type": "file",
                    "content": data,
                    "size": len(data),
                    "mode": 0o100644,
                    "mtime": time.time(),
                }
                # Ensure parent dir exists
                tree.setdefault(
                    "/", {"type": "dir", "children": {}, "mode": 0o40755, "size": 4096}
                )
                tree["/"]["children"][filename] = path
                continue

            # 4. Otherwise: regular tar extraction (gzip/zstd/plain)
            try:
                if "zstd" in media_type:
                    dctx = zstd.ZstdDecompressor()
                    tf = tarfile.open(
                        fileobj=dctx.stream_reader(io.BytesIO(data)), mode="r|"
                    )
                elif media_type.endswith("+gzip") or "+gzip" in media_type:
                    tf = tarfile.open(fileobj=io.BytesIO(data), mode="r|gz")
                else:
                    tf = tarfile.open(fileobj=io.BytesIO(data), mode="r|*")
            except tarfile.ReadError:
                print("     ↳ not a tar – treating as raw file (fallback)")
                filename = annotations.get(
                    "org.opencontainers.image.title", f"file-{digest[:12]}"
                )
                path = "/" + filename
                tree[path] = {
                    "type": "file",
                    "content": data,
                    "size": len(data),
                    "mode": 0o100644,
                    "mtime": time.time(),
                }
                tree["/"]["children"][filename] = path
                continue

            # 5. Normal tar extraction
            for member in tf:
                if (
                    not member.name
                    or member.name in (".", "./")
                    or member.name.startswith("./.")
                ):
                    continue
                path = "/" + member.name.lstrip("./")
                if member.isfile():
                    content = tf.extractfile(member).read()
                    tree[path] = {
                        "type": "file",
                        "content": content,
                        "size": len(content),
                        "mode": 0o100644 | (member.mode & 0o777),
                        "mtime": member.mtime or time.time(),
                    }
                    dirname = os.path.dirname(path)
                    tree.setdefault(
                        dirname,
                        {"type": "dir", "children": {}, "mode": 0o40755, "size": 4096},
                    )
                    tree[dirname]["children"][os.path.basename(path)] = path
            tf.close()

        with self._tree_lock:
            self.current_tree = tree

        print(f"[{time.strftime('%H:%M:%S')}] Mounted – {len(tree)} entries")

    def _reloader(self):
        last_digest = None
        while True:
            time.sleep(self.reload_interval)
            try:
                m = self.client.get_manifest(self.target)
                cur = m.get("config", {}).get("digest") or m["layers"][-1]["digest"]
                if last_digest and cur != last_digest:
                    print(
                        f"[{time.strftime('%H:%M:%S')}] New version detected → reloading"
                    )
                    self._load_new_tree()
                last_digest = cur
            except Exception as e:
                print(f"[{time.strftime('%H:%M:%S')}] Poll error: {e}")

    def _tree(self):
        with self._tree_lock:
            return self.current_tree or {}

    # ------------------- FUSE callbacks -------------------
    def getattr(self, path):
        tree = self._tree()
        node = tree.get(path) or tree.get(path + "/")
        if not node:
            return -errno.ENOENT

        is_dir = node["type"] == "dir"
        _stat = Stat()
        _stat.st_mode = node["mode"]
        _stat.st_nlink = 2 + len(node.get("children", {})) if is_dir else 1
        _stat.st_uid = os.getuid()
        _stat.st_gid = os.getgid()
        _stat.st_size = node.get("size", 4096)
        _stat.st_atime = time.time()
        _stat.st_mtime = node["mtime"]
        _stat.st_ctime = node["mtime"]
        return _stat

    def readdir(self, path):
        tree = self._tree()
        node = tree.get(path) or tree.get(path + "/")
        if not node or node["type"] != "dir":
            return -errno.ENOENT
        yield fuse.Direntry(".")
        yield fuse.Direntry("..")
        for name in sorted(node.get("children", {})):
            yield fuse.Direntry(name)

    def open(self, path, flags):
        tree = self._tree()
        if path not in tree or tree[path]["type"] != "file":
            return -errno.ENOENT
        if flags & 0b11:  # any write flag
            return -errno.EROFS
        return 0

    def read(self, path, size, offset):
        tree = self._tree()
        return tree[path]["content"][offset : offset + size]

    # --- Compatibility stubs (add these to HotReloadORASFuse) ---
    def access(self, path, mode):
        return 0  # everything is accessible

    def getxattr(self, path, name, position=0):
        return -errno.ENODATA

    def listxattr(self, path):
        return []

    def statfs(self, path):
        return dict(
            f_bsize=4096,
            f_blocks=999999999,
            f_bavail=999999999,
            f_files=1000000,
            f_ffree=1000000,
            f_namelen=255,
        )

    def readlink(self, path):
        return -errno.EINVAL

    # These are sometimes called even on read-only FS
    def chmod(self, path, mode):
        return -errno.EROFS

    def chown(self, path, uid, gid):
        return -errno.EROFS

    def utimens(self, path, times=None):
        # Update atime/mtime – harmless on read-only view
        tree = self._tree()
        node = tree.get(path) or tree.get(path + "/")
        if node:
            now = time.time()
            # atime = times[0] if times else now
            mtime = times[1] if times else now
            node["mtime"] = mtime
        return 0


def main():
    if len(sys.argv) < 3:
        print("""\
Usage: oras-fuse.py <mountpoint> <ref> [options]

  <mountpoint>                e.g. /mnt
  <ref>                       e.g. localhost:5000/hello:latest

Our options (can be anywhere after the two positional args):
  --insecure                  skip TLS verification
  --username USER --password PASS   basic auth
  --token TOKEN               bearer token

FUSE options (passed straight through):
  -f -d -o allow_other etc.

Examples:
  oras-fuse.py /mnt localhost:5000/hello:latest --insecure -f -d
  oras-fuse.py /mnt localhost:5000/hello:latest -f --insecure -o allow_other
""")
        sys.exit(1)

    mountpoint = sys.argv[1]
    target = sys.argv[2]

    # Parse our own flags
    username = password = token = None
    insecure = False

    # Build a clean argv that contains ONLY what FUSE may see
    fuse_argv = [sys.argv[0], mountpoint]  # program name
    i = 3
    while i < len(sys.argv):
        a = sys.argv[i]
        if a == "--insecure":
            insecure = True
            i += 1
        elif a in ("--username", "--password", "--token") and i + 1 < len(sys.argv):
            if a == "--username":
                username = sys.argv[i + 1]
            if a == "--password":
                password = sys.argv[i + 1]
            if a == "--token":
                token = sys.argv[i + 1]
            i += 2
        else:
            # give everything else to FUSE
            fuse_argv.append(a)
            # handle "-o value" correctly
            if (
                a == "-o"
                and i + 1 < len(sys.argv)
                and not sys.argv[i + 1].startswith("-")
            ):
                fuse_argv.append(sys.argv[i + 1])
                i += 1
            i += 1

    # Create filesystem instance
    server = HotReloadORASFuse(
        target=target,
        mountpoint=mountpoint,
        username=username,
        password=password,
        token=token,
        insecure=insecure,
        reload_interval=30,
    )
    fuse.Fuse.main(server, fuse_argv)


if __name__ == "__main__":
    main()
