import argparse

def n_sum(n: int):
    total = 0
    for i in range(n):
        total += i
    return total

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A simple function.")
    parser.add_argument("numbers", type=int, nargs="+", help="A list of numbers")
    
    args = parser.parse_args()
    
    stmts = [ f"faculty sum of n = {n_sum(n)}" for n in args.numbers ]
    print(stmts)