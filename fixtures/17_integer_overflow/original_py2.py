def check_overflow(val):
    res = val * 2
    return isinstance(res, (int, long))

if __name__ == "__main__":
    print(check_overflow(2**62))
