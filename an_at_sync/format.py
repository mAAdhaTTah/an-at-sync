import phonenumbers


def get_or_blank(dict_name, key):
    return dict_name.get(key, "")


def standardize_phone(phone_number: str):
    try:
        phone = phonenumbers.parse("+%s" % phone_number)
        return phonenumbers.format_number(
            phone, phonenumbers.PhoneNumberFormat.NATIONAL
        )
    except Exception:
        return phone_number


def convert_adr(adr):
    try:
        address_ln = (", ").join(get_or_blank(adr, "address_lines"))
    except Exception:
        address_ln = ""
    return (
        address_ln,
        get_or_blank(adr, "locality"),
        get_or_blank(adr, "region"),
        get_or_blank(adr, "postal_code"),
    )
