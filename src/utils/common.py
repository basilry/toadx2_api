import urllib.parse


def url_encode_key(key):
    return urllib.parse.quote(key)
