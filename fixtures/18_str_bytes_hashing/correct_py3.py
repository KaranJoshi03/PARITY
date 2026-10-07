def check_identity(s):
    return isinstance(s, (str, bytes))

if __name__ == "__main__":
    print(check_identity(b"hello"))
