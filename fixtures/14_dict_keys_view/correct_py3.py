def pop_key(d):
    keys = list(d.keys())
    return keys[0]

if __name__ == "__main__":
    print(pop_key({"a": 1, "b": 2}))
