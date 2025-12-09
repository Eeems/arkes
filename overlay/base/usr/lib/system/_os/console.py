import os
import pty
import select
import subprocess
import sys
import termios


def bytes_to_stdout(line: bytes):
    _ = sys.stdout.buffer.write(line)
    _ = sys.stdout.flush()


def bytes_to_stderr(line: bytes):
    _ = sys.stderr.buffer.write(line)
    _ = sys.stderr.flush()


def bytes_to_iec(size_bytes: int) -> str:
    units = ["KiB", "MiB", "GiB", "TiB", "PiB"]
    size = float(size_bytes)
    res = str(size_bytes)
    while size >= 1024.0 and units:
        size /= 1024.0
        unit = units.pop(0)
        res = f"{size:.2f} {unit}"
    return res


def shell(*args: str):
    master_fd, slave_fd = pty.openpty()
    proc = subprocess.Popen(
        args,
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        close_fds=True,
        preexec_fn=os.setsid,
    )
    os.close(slave_fd)
    old_tty = termios.tcgetattr(sys.stdin.fileno())
    try:
        import tty

        _ = tty.setraw(sys.stdin.fileno())
        while proc.poll() is None:
            r, _, _ = select.select([sys.stdin.fileno(), master_fd], [], [], 0.1)
            if sys.stdin.fileno() in r:
                data = os.read(sys.stdin.fileno(), 1024)
                if not data:
                    break

                _ = os.write(master_fd, data)

            if master_fd in r:
                try:
                    data = os.read(master_fd, 1024)
                    if not data:
                        break

                    _ = os.write(sys.stdout.fileno(), data)

                except OSError as e:
                    if e.errno == 5:
                        break

    except KeyboardInterrupt:
        pass

    finally:
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old_tty)
        _ = proc.wait()
