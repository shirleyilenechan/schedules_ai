import calendar
import random
from datetime import timedelta

import pandas as pd
import pytz


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


def generate_shift_info(row, user_colors):
    return (
        f"<span class='shift' style='color: {user_colors[row['user']]};'>"
        f"{row['user']}: "
        f"{row['shift_start_datetime'].strftime('%I:%M %p')} - "
        f"{row['shift_end_datetime'].strftime('%I:%M %p')}"
        f"</span>"
    )


def dataframe_to_html_calendar(df: pd.DataFrame, timezone: str) -> str:
    # Convert shift_start_datetime to datetime objects and ensure they're in UTC
    df["shift_start_datetime"] = pd.to_datetime(df["shift_start_datetime"])

    # Get unique users and assign colors
    users = df["user"].unique()
    colors = generate_random_colors(len(users))
    user_colors = dict(zip(users, colors))

    # Get the start and end dates from the dataframe
    start_date = df["shift_start_datetime"].min()
    end_date = df["shift_start_datetime"].max()

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
                    tz = pytz.timezone(timezone)
                    date = current_date.replace(day=day)
                    date = date.astimezone(tz)
                    day_shifts = df[df["shift_start_datetime"].dt.date == date.date()]
                    if not day_shifts.empty:
                        shift_info = "<br>".join(
                            [
                                generate_shift_info(row, user_colors)
                                for _, row in day_shifts.iterrows()
                            ]
                        )
                        html_calendar += (
                            f"<td style='vertical-align: top; height: 100px; "
                            f"width: 14%;'><strong>{day}</strong><br>{shift_info}</td>"
                        )
                    else:
                        html_calendar += (
                            f"<td style='vertical-align: top; height: 100px; "
                            f"width: 14%;'><strong>{day}</strong></td>"
                        )
            html_calendar += "</tr>"

        html_calendar += "</table><br>"
        current_date = (current_date.replace(day=28) + timedelta(days=4)).replace(day=1)

    return html_calendar
