def first_byte(s):
    if isinstance(s, bytes):
        return s.decode("ascii")[0]
    return s[0]

if __name__ == "__main__":
    print(first_byte(b"hello"))
