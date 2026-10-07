def concat_test(a, b):
    try:
        return a + b
    except TypeError:
        return "TypeError"

if __name__ == "__main__":
    print(concat_test(b"hello", " world"))
