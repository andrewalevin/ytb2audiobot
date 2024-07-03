
def round_to_10(number):
    return round(number / 10) * 10


def predict_downloading_time(duration):
    time = int(0.04 * duration + 10)
    return round_to_10(time)
