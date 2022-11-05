def str_to_id(value: str) -> str:
    return value.translate ({ord(c): "_" for c in "!@#$%^&*()[]{};:,./<>?\|`~-=_+ "})


def get_dev_identifiers(identifiers: str) -> tuple[str, str]:
    ident_data = list(identifiers)
    domain = ident_data[0][0]
    dev_ident = ident_data[0][1]
    return (domain, dev_ident)

    
