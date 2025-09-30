
def get_dev_identifiers(identifiers: str) -> tuple[str, str]:
    # import pdb;pdb.set_trace()
    ident_data = list(identifiers)
    try:
        domain = ident_data[0][0]
        dev_ident = ident_data[0][1]
        return (domain, dev_ident)
    except IndexError:
        return ("", "")
