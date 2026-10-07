def sort_with_cmp(lst):
    def my_cmp(a, b):
        return a - b
    return sorted(lst, cmp=my_cmp)

if __name__ == "__main__":
    print(sort_with_cmp([3, 1, 2]))
