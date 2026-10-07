def process_list(nums):
    m = list(map(lambda x: x * 2, nums))
    return len(m)

if __name__ == "__main__":
    print(process_list([1, 2, 3]))
