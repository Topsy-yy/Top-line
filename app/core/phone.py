import re
from fastapi import HTTPException, status

def normalize_phone(phone: str) -> str:
    """
    Normalizes Kenyan & international phone numbers.
    E.g.:
      0712345678 -> +254712345678
      712345678  -> +254712345678
      254712345678 -> +254712345678
      +254712345678 -> +254712345678
    """
    clean = re.sub(r"[\s\-\(\)]", "", phone.strip())
    if clean.startswith("+"):
        digits = clean[1:]
    else:
        digits = clean

    if not digits.isdigit():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Phone number must contain only valid digits."
        )

    if len(digits) == 9 and digits.startswith(("7", "1")):
        return f"+254{digits}"
    elif len(digits) == 10 and digits.startswith(("07", "01")):
        return f"+254{digits[1:]}"
    elif len(digits) == 12 and digits.startswith("254"):
        return f"+{digits}"
    elif clean.startswith("+"):
        return clean
    else:
        # Default with leading +
        return f"+{digits}"

