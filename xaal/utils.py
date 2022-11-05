from typing import Tuple

def str_to_id(value: str) -> str:
    return value.translate ({ord(c): "_" for c in "!@#$%^&*()[]{};:,./<>?\|`~-=_+ "})


def extract_device_identifiers(identifiers: str) -> Tuple(str, str):
    ident_data = list(identifiers)
    domain = ident_data[0][0]
    dev_ident = ident_data[0][1]
    return (domain, dev_ident)

    
