from strutil import reverse, shout

def test_reverse():
    assert reverse('abc') == 'cba'

def test_shout():
    assert shout('hi') == 'HI!'
