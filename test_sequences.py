"""
Verifies the app against the exact example sequences from the spec.
Run against a live deployment: python test_sequences.py [BASE_URL]
"""
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8080"

passed = 0
failed = 0


def _get(path: str) -> tuple[int, str]:
    """Returns (status_code, body_text)."""
    try:
        with urllib.request.urlopen(f"{BASE}{path}") as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def check(description: str, url: str, expected: str) -> None:
    global passed, failed
    _, actual = _get(url)
    ok = actual == expected
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {description}: {url} -> expected {expected!r}, got {actual!r}")
    if ok:
        passed += 1
    else:
        failed += 1


def sequence_1() -> None:
    print("\n=== Sequence 1 ===")
    check("set ex", "/set?name=ex&value=10", "ex = 10")
    check("get ex", "/get?name=ex", "10")
    check("unset ex", "/unset?name=ex", "ex = None")
    check("get ex after unset", "/get?name=ex", "None")
    check("end", "/end", "CLEANED")


def sequence_2() -> None:
    print("\n=== Sequence 2 ===")
    check("set a", "/set?name=a&value=10", "a = 10")
    check("set b", "/set?name=b&value=10", "b = 10")
    check("numequalto 10", "/numequalto?value=10", "2")
    check("numequalto 20", "/numequalto?value=20", "0")
    check("set b=30", "/set?name=b&value=30", "b = 30")
    check("numequalto 10 again", "/numequalto?value=10", "1")
    check("end", "/end", "CLEANED")


def sequence_3() -> None:
    print("\n=== Sequence 3 ===")
    check("set a", "/set?name=a&value=10", "a = 10")
    check("set b", "/set?name=b&value=20", "b = 20")
    check("get a", "/get?name=a", "10")
    check("get b", "/get?name=b", "20")
    check("undo (unset b)", "/undo", "b = None")
    check("get a still 10", "/get?name=a", "10")
    check("get b now None", "/get?name=b", "None")
    check("set a=40", "/set?name=a&value=40", "a = 40")
    check("get a=40", "/get?name=a", "40")
    check("undo (a back to 10)", "/undo", "a = 10")
    check("get a=10", "/get?name=a", "10")
    check("undo (a back to None)", "/undo", "a = None")
    check("get a=None", "/get?name=a", "None")
    check("undo with nothing left", "/undo", "NO COMMANDS")
    check("redo (a=10)", "/redo", "a = 10")
    check("redo (a=40)", "/redo", "a = 40")
    check("end", "/end", "CLEANED")


def graceful_input_handling() -> None:
    global passed, failed
    print("\n=== Graceful handling of unexpected input ===")
    status, _ = _get("/set?name=x")
    ok = status == 400
    print(f"[{'PASS' if ok else 'FAIL'}] missing 'value' param -> expected 400, got {status}")
    if ok:
        passed += 1
    else:
        failed += 1


if __name__ == "__main__":
    sequence_1()
    sequence_2()
    sequence_3()
    graceful_input_handling()

    _get("/end")  # always leave the datastore clean

    print(f"\n{'=' * 40}")
    print(f"TOTAL: {passed} passed, {failed} failed")
    print("=" * 40)
    sys.exit(1 if failed else 0)
