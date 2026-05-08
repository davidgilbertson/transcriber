from difflib import SequenceMatcher

a = "This is a test to see how it's going to write out .env or readme.md, whether it understands agents.md, and how it would spell runtranscriber.py."
b = "This is a test to see how it can write out .env or README.md, whether it understands agents.md, and how it would spell run_transcriber.py."

matcher = SequenceMatcher(a=a, b=b)

for tag, i1, i2, j1, j2 in matcher.get_opcodes():
    print(
        "{:7}   a[{}:{}] --> b[{}:{}] {!r:>8} --> {!r}".format(
            tag, i1, i2, j1, j2, a[i1:i2], b[j1:j2]
        )
    )
