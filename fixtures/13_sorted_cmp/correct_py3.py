from functools import cmp_to_key
def sort_with_cmp(lst):
    def my_cmp(a, b):
        return a - b
    return sorted(lst, key=cmp_to_key(my_cmp))

if __name__ == "__main__":
    print(sort_with_cmp([3, 1, 2]))
