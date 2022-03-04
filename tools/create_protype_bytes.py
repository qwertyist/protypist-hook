text = input("Sök efter denna sträng:\n")
print(" 00 ".join("{:02x}".format(ord(c)) for c in text) + " 00")