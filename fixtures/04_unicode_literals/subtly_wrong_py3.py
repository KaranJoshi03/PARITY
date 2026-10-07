def check_is_text(s):
    return isinstance(s, (str, unicode))

if __name__ == "__main__":
    print(check_is_text("hello"))
