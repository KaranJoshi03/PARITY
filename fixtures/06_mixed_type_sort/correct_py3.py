def sort_mixed(items):
    return sorted(items, key=lambda x: (type(x).__name__, x))

if __name__ == "__main__":
    print(sort_mixed([1, "a", 2]))
