import argparse

def n_sum(n: int):
    total = 0
    for i in range(n):
        total += i
    return total

def main(numbers):
    for n in numbers:
        print(f"faculty sum of n = {n_sum(n)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A simple function.")
    parser.add_argument("numbers", type=int, nargs="+", help="A list of numbers")
    
    args = parser.parse_args()
    
    main(args.numbers)