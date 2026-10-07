def sum_all(lst):
    return reduce(lambda x, y: x + y, lst)

if __name__ == "__main__":
    print(sum_all([1, 2, 3, 4]))
