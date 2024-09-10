import calendar
import random
from datetime import timedelta

import pandas as pd


def generate_random_colors(n):
    colors = []
    for _ in range(n):
        r = random.randint(100, 255)
        g = random.randint(100, 255)
        b = random.randint(100, 255)
        color = "#{:02x}{:02x}{:02x}".format(r, g, b)
        colors.append(color)
    return colors


def generate_color_dict(df):
    users = df["user"].unique()
    colors = generate_random_colors(len(users))
    return dict(zip(users, colors))


def dataframe_to_html_calendar(df: pd.DataFrame, timezone: str) -> str:
    user_colors = generate_color_dict(df)

    df["shift_start_datetime"] = pd.to_datetime(
        df["shift_start_datetime"]
    ).dt.tz_convert(timezone)
    df["shift_end_datetime"] = pd.to_datetime(df["shift_end_datetime"]).dt.tz_convert(
        timezone
    )

    start_date = df["shift_start_datetime"].min()
    end_date = df["shift_end_datetime"].max()

    html_calendar = """
    <style>
        table { border-collapse: separate; border-spacing: 1px; width: 100%; background-color: #000000; color: #ffffff; }
        th, td { padding: 8px; text-align: left; vertical-align: top; }
        th { background-color: #333333; }
        td { position: relative; height: 80px; }
        .date { position: absolute; top: 5px; left: 5px; }
        .shift-container { position: absolute; top: 30px; left: 0; right: 0; height: 25px; display: flex; }
        .shift { flex: 1; margin: 0 1px; padding: 2px; color: black; overflow: hidden; position: relative; }
        .shift-text { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; font-size: 0.8em; text-align: center; }
    </style> 
    """  # noqa E501

    current_date = start_date.replace(day=1)

    while current_date <= end_date:
        cal = calendar.monthcalendar(current_date.year, current_date.month)
        month_name = current_date.strftime("%B %Y")

        html_calendar += f"<h3 style='color: #ffffff;'>{month_name}</h3>"
        html_calendar += "<table>"
        html_calendar += "<tr><th>MONDAY</th><th>TUESDAY</th><th>WEDNESDAY</th><th>THURSDAY</th><th>FRIDAY</th><th>SATURDAY</th><th>SUNDAY</th></tr>"  # noqa E501

        for week in cal:
            html_calendar += "<tr>"
            for day in week:
                if day == 0:
                    html_calendar += "<td></td>"
                else:
                    date = current_date.replace(day=day)
                    next_date = date + timedelta(days=1)
                    day_shifts = df[
                        (
                            (df["shift_start_datetime"].dt.date <= date.date())
                            & (df["shift_end_datetime"].dt.date >= date.date())
                        )
                        | (
                            (df["shift_start_datetime"].dt.date <= date.date())
                            & (df["shift_end_datetime"].dt.date == next_date.date())
                            & (
                                df["shift_end_datetime"].dt.time
                                == pd.Timestamp("00:00:00").time()
                            )
                        )
                    ]

                    html_calendar += f"<td><div class='date'>{day}</div><div class='shift-container'>"  # noqa E501

                    if not day_shifts.empty:
                        for _, row in day_shifts.iterrows():
                            bg_color = user_colors[row["user"]]
                            shift_start = row["shift_start_datetime"].date()
                            shift_end = row["shift_end_datetime"].date()

                            style = f"background-color: {bg_color};"

                            if date.date() == shift_start:
                                style += "border-top-left-radius: 4px; border-bottom-left-radius: 4px;"  # noqa E501
                            if date.date() == shift_end or (
                                shift_end == next_date.date()
                                and row["shift_end_datetime"].time()
                                == pd.Timestamp("00:00:00").time()
                            ):
                                style += "border-top-right-radius: 4px; border-bottom-right-radius: 4px;"  # noqa E501

                            html_calendar += f"<div class='shift' style='{style}'>"
                            if date.date() == shift_start:
                                shift_text = f"{row['user']}: {row['shift_start_datetime'].strftime('%I:%M %p')} - {row['shift_end_datetime'].strftime('%I:%M %p')}"  # noqa E501
                                html_calendar += f"<span class='shift-text' title='{shift_text}'>{shift_text}</span>"  # noqa E501
                            html_calendar += "</div>"

                    html_calendar += "</div></td>"
            html_calendar += "</tr>"

        html_calendar += "</table><br>"
        current_date = (current_date.replace(day=28) + timedelta(days=4)).replace(day=1)

    return html_calendar
