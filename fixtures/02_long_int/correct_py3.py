def check_large_int(x):
    return isinstance(x, int)

if __name__ == "__main__":
    print(check_large_int(2**65))
