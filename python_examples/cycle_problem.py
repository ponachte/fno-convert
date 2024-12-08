def double_string(text : str):
    return text + text

def power_string(text: str):
    text = double_string(text)
    text = double_string(text)
    return text