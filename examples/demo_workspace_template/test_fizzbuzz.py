from fizzbuzz import fizzbuzz


def test_empty():
    assert fizzbuzz(0) == []
    assert fizzbuzz(-2) == []


def test_rules():
    assert fizzbuzz(15) == [
        "1", "2", "Fizz", "4", "Buzz", "Fizz", "7", "8", "Fizz", "Buzz",
        "11", "Fizz", "13", "14", "FizzBuzz",
    ]

