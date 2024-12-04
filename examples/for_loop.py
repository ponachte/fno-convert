def sum_array(arr):
    total = 0
    for element in arr:
        total += int(element)
    return total

def n_sum(n: int):
    total = 0
    for i in range(n):
        total += i
    return total

if __name__ == "__main__":
    for n in range(10):
        print(n_sum(n))