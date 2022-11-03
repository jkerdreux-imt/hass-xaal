
def str_to_id(value: str):
    return value.translate ({ord(c): "_" for c in "!@#$%^&*()[]{};:,./<>?\|`~-=_+ "})

