from rnd.util import find_numbers, format_value, numbers_match, slugify


def nums(text):
    return [n.value for n in find_numbers(text)]


def test_find_numbers_ignores_codes_and_labels():
    assert nums("KS-204 cracked at 38,500 cycles in P2") == [38500]
    assert nums("rPP-50 costs $4.45 and 45% of units") == [4.45, 45]
    assert nums("148k cycles, 1.2M units") == [148000, 1200000]


def test_rounding_at_written_precision():
    (claim,) = find_numbers("148,250")
    assert numbers_match(claim, [148250.0])
    (claim,) = find_numbers("11.6")
    assert numbers_match(claim, [11.6])
    (claim,) = find_numbers("12")
    assert numbers_match(claim, [11.6])  # rounding to the written (integer) precision
    (claim,) = find_numbers("12.5")
    assert not numbers_match(claim, [11.6])


def test_coarse_rounding_needs_an_approximation_word():
    (bare,) = find_numbers("110,000 cycles")
    assert not numbers_match(bare, [107833.33])
    (approx,) = find_numbers("about 110,000 cycles")
    assert numbers_match(approx, [107833.33])
    (k,) = find_numbers("108k cycles")
    assert numbers_match(k, [107833.33])


def test_percent_matches_fraction():
    (p,) = find_numbers("46.81%")
    assert numbers_match(p, [0.4681])
    assert numbers_match(p, [46.81])
    assert not numbers_match(p, [0.4781])


def test_format_value_is_exact():
    assert format_value(0.1) == "0.1"
    assert format_value(148250.0) == "148250"
    assert format_value(0.45, "0%") == "45%"


def test_slugify_handles_vietnamese():
    assert slugify("Báo cáo thử nghiệm ghế Đà Nẵng") == "bao-cao-thu-nghiem-ghe-da-nang"
