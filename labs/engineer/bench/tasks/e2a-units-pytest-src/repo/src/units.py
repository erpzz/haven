def c_to_f(c):
    return c * 9 / 5 - 32

def f_to_c(f):
    return (f - 32) * 5 / 9

def km_to_miles(km):
    if km < 0:
        raise ValueError('distance cannot be negative')
    return km * 0.621371
