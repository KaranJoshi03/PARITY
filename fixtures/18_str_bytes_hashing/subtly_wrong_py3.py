def check_identity(s):
    return isinstance(s, str)  # Assumes Py2 where bytes==str

if __name__ == "__main__":
    print(check_identity(b"hello"))
