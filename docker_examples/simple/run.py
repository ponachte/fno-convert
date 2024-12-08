NUMBERS = [1, 2, 3, 4]

def n_sum(n: int):
    total = 0
    for i in range(n):
        total += i
    return total

if __name__ == "__main__":
    for n in NUMBERS:
        print(f"faculty sum of n = {n_sum(n)}")