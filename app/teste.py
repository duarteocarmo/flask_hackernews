from datetime import datetime


def get_score(time, score, gravity=1.8):
    datetime_difference = datetime.utcnow() - time
    hours_passed = (
        datetime_difference.days * 24 + datetime_difference.seconds / 3600
    )
    return (score - 1) / pow((hours_passed + 2), gravity)
