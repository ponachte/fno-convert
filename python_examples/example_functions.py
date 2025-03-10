def simple_sum(a: int, b: int):
    return a + b

def divide(numerator: int, denominator: int):
    if denominator > 0:
        return numerator / denominator
    else:
        return "niet delen door 0!"

def binarycount(bits):

    count = 0
    for i, bit in enumerate(bits):
        if bit == 1:
            count = count + 2**i
    
    return count

def binarycount2(bit1 : int, bit2 : int):

    out = 0

    if bit1:
        if bit2:
            out = 3
        else:
            out = 2
    else:
        if bit2:
            out = 1
    
    return out

def filter_list(numbers, min):
    filtered = []
    for number in numbers:
        if number >= min:
            filtered.append(number)
    return filtered
    
