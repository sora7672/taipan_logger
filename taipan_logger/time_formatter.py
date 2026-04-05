"""
Provides a custom datetime formatting function using human-readable placeholder tokens.
Placeholders are replaced longest-first to avoid partial matches between overlapping tokens.

:author: sora7672
"""

__author__: str = "sora7672"

from datetime import datetime


def get_datetime_string_by_format(format_string: str) -> str:
    """
    Converts a format string into a datetime string using the given placeholders.
    Placeholders are replaced longest-first to avoid partial matches.

    Example datetime: 2026.04.15 - 19:38:27:234

    Placeholders:
        yyyy / YYYY  -> 2026
        yy   / YY    -> 26
        MM           -> 04 (month with leading zero)
        M            -> 4  (month without leading zero)
        dd   / DD    -> 15 (day with leading zero)
        d    / D     -> 9  (day without leading zero)
        hh   / HH    -> 19 (hour with leading zero)
        h    / H     -> 6  (hour without leading zero)
        mm           -> 38 (minute with leading zero)
        m            -> 3  (minute without leading zero)
        ss           -> 27 (second with leading zero)
        s            -> 2  (second without leading zero)
        mimimi       -> 234 (milliseconds, 3 digits)
        mimi         -> 23  (milliseconds, 2 digits)
        mi           -> 2   (milliseconds, 1 digit)

    Example usage:
        format_string: "[yyyy-MM-dd] [hh:mm:ss:mimimi]"
        result:        "[2026-04-15] [19:38:27:234]"

        format_string: "yyyy/MM/dd_hh-mm"
        result:        "2026/04/15_19-38"

        format_string: "LOG_dd.MM.yy"
        result:        "LOG_15.04.26"

    :param format_string: str - the format string containing placeholders
    :return: str - the formatted datetime string
    """
    current_time: datetime = datetime.now()
    micro_seconds_now: str = current_time.strftime("%f")
    date_now: str = current_time.strftime("%Y%m%d")
    time_now: str = current_time.strftime("%H%M%S")

    formatter_dict: dict[str, str] = {
        "mimimi": micro_seconds_now[:3],
        "mimi":   micro_seconds_now[:2],
        "yyyy":   date_now[0:4],
        "YYYY":   date_now[0:4],
        "mi":     micro_seconds_now[:1],
        "MM":     date_now[4:6],
        "dd":     date_now[6:8],
        "DD":     date_now[6:8],
        "hh":     time_now[0:2],
        "HH":     time_now[0:2],
        "ss":     time_now[4:6],
        "yy":     date_now[2:4],
        "YY":     date_now[2:4],
        "mm":     time_now[2:4],
        "M":      str(int(date_now[4:6])),
        "d":      str(int(date_now[6:8])),
        "D":      str(int(date_now[6:8])),
        "h":      str(int(time_now[0:2])),
        "H":      str(int(time_now[0:2])),
        "m":      str(int(time_now[2:4])),
        "s":      str(int(time_now[4:6])),
        "S":      str(int(time_now[4:6]))
    }

    new_formatted_string: str = format_string
    for k, v in formatter_dict.items():
        new_formatted_string = new_formatted_string.replace(k, v)

    return new_formatted_string


if __name__ == "__main__":
    print("Dont start the package files alone! The imports wont work like this!")