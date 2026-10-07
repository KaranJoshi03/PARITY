def concat_test(a, b):
    if isinstance(a, bytes):
        a = a.decode("utf-8")
    return a + b

if __name__ == "__main__":
    print(concat_test(b"hello", " world"))
