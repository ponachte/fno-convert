def faculty(n : int):
    if n == 1:
        return 1
    return n * faculty(n-1)