import threading

from normt2s import Normalizer


def test_concurrent_edit_and_normalize():
    n = Normalizer("en")
    n.add_abbreviation("foo", "alpha")
    text = "foo costs 5 kg"
    valid = {"alpha costs five kilograms", "beta costs five kilograms"}
    stop = threading.Event()
    errors, bad = [], []

    def work():
        try:
            while not stop.is_set():
                out = n.normalize(text)
                if out not in valid:
                    bad.append(out)
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    def edit():
        for i in range(60):
            n.add_abbreviation("foo", "beta" if i % 2 else "alpha")
            n.add_abbreviation(f"x{i}", "y")
        stop.set()

    threads = [threading.Thread(target=work) for _ in range(16)]
    editor = threading.Thread(target=edit)
    for t in threads:
        t.start()
    editor.start()
    editor.join()
    for t in threads:
        t.join()
    assert not errors and not bad
