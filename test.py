rates_standardised = {}
rates_standardised["USD"] = {
    "buy": "hola",
    "sell": "chau"
    }

def has_key(dict, key):
    try:
        x = dict[key]
        return True
    except KeyError:
        return False

print(has_key(rates_standardised, "EUR"))
print(has_key(rates_standardised, "ARS"))
print(has_key(rates_standardised, "USD"))
print(has_key(rates_standardised, "BTC"))