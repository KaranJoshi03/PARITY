import math
def round_val(x):
    if x > 0:
        return float(math.floor(x + 0.5))
    return float(math.ceil(x - 0.5))

if __name__ == "__main__":
    print(round_val(2.5))
