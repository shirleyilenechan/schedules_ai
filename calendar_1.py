import calendar
import random
from datetime import timedelta

import pandas as pd


def generate_random_colors(n):
    colors = []
    for _ in range(n):
        # Generate random RGB values
        r = random.randint(100, 255)
        g = random.randint(100, 255)
        b = random.randint(100, 255)

        # Convert to hex
        color = "#{:02x}{:02x}{:02x}".format(r, g, b)
        colors.append(color)
    return colors


def dataframe_to_html_calendar(df: pd.DataFrame, timezone: str) -> str:
    """Converts a DataFrame of shifts to an HTML calendar representation.

    Args:
        df (pd.DataFrame): A DataFrame containing shift information with columns:
            - user: The name of the person assigned to the shift.
            - shift_start_datetime: The start time of the shift in UTC timezone.
            - shift_duration: The duration of the shift in minutes.
        timezone (str): The target timezone for displaying the shift times.

    Returns:
        str: A string containing an HTML representation of a calendar shifts
         highlighted.
    """
    # Convert shift_start_datetime to datetime objects
    df["shift_start_datetime"] = pd.to_datetime(df["shift_start_datetime"], utc=True)

    # Get unique users and assign colors
    users = df["user"].unique()
    colors = generate_random_colors(len(users))
    user_colors = dict(zip(users, colors))

    # Get the start and end dates from the dataframe
    start_date = df["shift_start_datetime"].min()
    end_date = df["shift_start_datetime"].max()

    # Create a calendar for each month
    html_calendar = "<style>.shift { margin: 1px 0; }</style>"
    current_date = start_date.replace(day=1)

    while current_date <= end_date:
        cal = calendar.monthcalendar(current_date.year, current_date.month)
        month_name = current_date.strftime("%B %Y")

        html_calendar += f"<h3>{month_name}</h3>"
        html_calendar += (
            "<table border='1' style='border-collapse: collapse; width: 100%;'>"
        )
        html_calendar += (
            "<tr><th>Mon</th><th>Tue</th><th>Wed</th><th>Thu</th><th>Fri</th>"
            "<th>Sat</th><th>Sun</th></tr>"
        )

        for week in cal:
            html_calendar += "<tr>"
            for day in week:
                if day == 0:
                    html_calendar += "<td></td>"
                else:
                    date = current_date.replace(day=day)
                    day_shifts = df[df["shift_start_datetime"].dt.date == date.date()]

                    if not day_shifts.empty:
                        # Ignore E501 because of long f-string expression
                        shift_info = "<br>".join(
                            [
                                "<span class='shift' style='color: "
                                f"{user_colors[row['user']]};'>{row['user']}: "
                                f"{row['shift_start_datetime'].tz_convert(timezone).strftime('%I:%M %p')} - "  # noqa: E501
                                f"{(row['shift_start_datetime'] + pd.Timedelta(row['shift_duration'])).tz_convert(timezone).strftime('%I:%M %p')}"  # noqa: E501
                                f"</span>"
                                for _, row in day_shifts.iterrows()
                            ]
                        )
                        html_calendar += (
                            "<td style='vertical-align: top; height: 100px; "
                            f"width: 14%;'><strong>{day}</strong><br>{shift_info}</td>"
                        )
                    else:
                        html_calendar += (
                            "<td style='vertical-align: top; height: 100px; "
                            f"width: 14%;'><strong>{day}</strong></td>"
                        )
            html_calendar += "</tr>"

        html_calendar += "</table><br>"
        current_date = (current_date.replace(day=28) + timedelta(days=4)).replace(day=1)

    return html_calendar
