def my_sort(text: str):
    return str(sorted(text))

def sort_texts(text1: str, text2: str):
    return my_sort(text1) + my_sort(text2)