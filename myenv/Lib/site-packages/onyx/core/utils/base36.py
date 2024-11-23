###############################################################################
#
#   Copyright: (c) 2015 Carlo Sbraccia
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
###############################################################################

import uuid

__all__ = ["b36encode", "unique_id"]

ALPHABET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'


# -----------------------------------------------------------------------------
def b36encode(hexdigest):
    """
    Description:
        Encode a hexadecimal bynary string in base36. The choice of base 36
        is convenient in that the digits can be represented using the arabic
        numerals 0–9 and the Latin letters A–Z.
        (http://en.wikipedia.org/wiki/Base_36)
    Inputs:
        hexdigest - a hexadecimal bynary string
    Returns:
        A string.
    Example:
        b36encode(hashlib.md5(b"abc-def").hexdigest())
    """
    number = int(hexdigest, 16)

    base36 = ""
    while number:
        number, k = divmod(number, 36)
        base36 = ALPHABET[k] + base36

    return base36 or ALPHABET[0]


# -----------------------------------------------------------------------------
def unique_id(nchars=8):
    """
    Description:
        Return pseudo-unique identifier of nchars alpha-numeric characters
        based on a random UUID.
    Inputs:
        nchars - number of characters in the unique ID (default is 8, which
                 gives 282.e10 distinct possibilities)
    Returns:
        A string.
    """
    if nchars > 25:
        raise ValueError("maximum number of characters is 25")
    buuid = bytes(str(uuid.uuid4()).replace("-", ""), "utf-8")
    return b36encode(buuid)[:nchars]
