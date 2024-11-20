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