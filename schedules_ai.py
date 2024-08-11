from datetime import datetime as dt
from datetime import timedelta, timezone, tzinfo
from typing import List, Literal, Optional

import pytz
from langchain_core.pydantic_v1 import (
    BaseModel,
    Field,
    conint,
    root_validator,
    validator,
)

import pd_timezones


def is_valid_timezone(tz_identifier):
    pd_tz = pd_timezones.timezones
    # Check if the provided tz_identifier is in the list of valid timezones
    return tz_identifier in pd_tz


def is_timezone_aware(date_time):
    return tzinfo is not None


def get_matching_restriction(restrictions, start_day_of_week):
    for restriction in restrictions:
        if restriction.start_day_of_week == start_day_of_week:
            return restriction


def get_start_time(rotation, values):
    tz = pytz.timezone(values["timezone"])

    day_of_week = rotation.isoweekday()
    restriction = get_matching_restriction(values["restrictions"], day_of_week)

    start_time = dt.strptime(restriction.start_time_of_day, "%H:%M:%S").time()

    rotation = rotation.astimezone(tz)
    rotation = rotation.replace(
        hour=start_time.hour, minute=start_time.minute, second=start_time.second
    )

    return rotation


class User(BaseModel):
    user_name: str = Field(description="The names of the users in the group.")
    type: Literal["user_reference"] = Field(
        description="The value in this field should always be 'user_reference'."
    )


class Restriction(BaseModel):
    type: Literal["daily_restriction", "weekly_restriction"] = Field(
        description=(
            "For each week, check which user(s) work during the week. If the same user"
            " works all of the shifts that week, that week is considered a"
            " weekly_shift. If every week is a weekly_shift, then the value"
            " is weekly_restriction."
        )
    )
    duration_seconds: conint(gt=0) = Field(  # type: ignore
        description="Time delta between shift start - shift end, measured in seconds."
    )
    start_time_of_day: str = Field(
        regex="^([01]?[0-9]|2[0-3]):([0-5]?[0-9]):([0-5]?[0-9])$",
        description=(
            "Start time for start_day_of_week,"
            " represented as a string in HH:mm:ss format."
        ),
    )
    start_day_of_week: int = Field(
        description=(
            "Day of the week the shift occurs,"
            " represented in ISO 8601 day format (1 is Monday, 7 is Sunday)."
            " Mon = 1, Tue = 2, Wed = 3, Thurs = 4, Fri = 5, Sat = 6, Sun = 7"
        )
    )

    @validator("start_time_of_day", pre=True)
    def validate_start_time(cls, v: str):
        # Attempt to parse the string into a datetime object then convert to time
        try:
            dt.strptime(v, "%H:%M:%S").time()
        except ValueError:
            raise ValueError(f"{v} is not a valid time")
        # Since the field expects a string, convert the time object back to string
        return v

    @validator("start_day_of_week", pre=True)
    def validate_isoweekday(cls, v):
        if not 1 <= v <= 7:
            raise ValueError(f"{v} is not a valid iso weekday")
        return v


class ScheduleLayers(BaseModel):
    timezone: str = Field(
        regex="^[\w/]+$",
        description=(
            "The timezone for a group of users."
            " Timezones must be a valid timezone name as defined by datetime.tzname()."
        ),
    )
    num_shifts: int = Field(
        description=(
            "How often the rotation occurs. Examples: each day, every day, each week, "
            "every week, every 3 days, every 2 days, every 2 weeks, every three weeks."
        )
    )
    start: dt = Field(
        description=(
            "The group's first shift, represented as a datetime object."
            " start must be timezone aware. start must also be a future date."
        )
    )
    rotation_virtual_start: dt = Field(
        description=(
            "The rotation start provided by the user, represented as a datetime object."
            " rotation_virtual_start must be timezone aware."
            " rotation_virtual_start must also be a future date."
        )
    )
    end: Optional[dt] = Field(
        default=None,
        description=(
            "End date and time for a group of users, represented as a datetime object."
            " End must be timezone aware. If provided, end must also be a future date."
        ),
    )
    rotation_turn_length_seconds: Literal[86400, 604800] = Field(
        description=(
            "If the group's restrictions are daily_restriction, "
            "then rotation_turn_length_seconds is 86400. "
            "If the group's restrictions are weekly_restriction, "
            "then rotation_turn_length_seconds is 604800. "
            "rotation_turn_length_seconds is determined by the "
            "group's restriction type."
        )
    )
    users: List[User] = Field(
        description=("A list of user objects, representing each user in the group.")
    )
    restrictions: List[Restriction] = Field(
        description="A list of restriction objects for the group."
    )

    original_users: List[User] = Field(description=("A copy of the users list."))

    spans_multiple_days: bool = Field(
        description=("True if the shift spans multiple days. False otherwise")
    )

    everyday: bool = Field(
        description=("True if the shift occurs every day, False otherwise.")
    )

    @root_validator(pre=True)
    def generate_user_list(cls, values):
        num_shifts = values.get("num_shifts", 1)
        original_users = values.get("original_users", [])

        expanded_users = []
        for user in original_users:
            for _ in range(num_shifts):
                expanded_users.append(user)
        values["users"] = expanded_users
        return values

    @root_validator(pre=True)
    def everyday_restriction(cls, values):
        everyday = values.get("everyday", False)
        restrictions = values.get("restrictions", [])

        if everyday:
            # Get the details from the first restriction
            first_restriction = restrictions[0]
            if first_restriction:
                start_time = first_restriction["start_time_of_day"]
                duration = first_restriction["duration_seconds"]
                restriction_type = first_restriction["type"]
            new_restrictions = [
                Restriction(
                    type=restriction_type,
                    start_time_of_day=start_time,
                    duration_seconds=duration,
                    start_day_of_week=day,
                )
                for day in range(1, 8)  # 1 to 7, representing Monday to Sunday
            ]
            values["restrictions"] = new_restrictions

        return values

    @root_validator
    def adjust_start_date(cls, values):
        if not values["restrictions"]:
            return

        days_of_week = [r.start_day_of_week for r in values["restrictions"]]

        # If rotation_virtual_start is already on the correct day, use it
        if values["rotation_virtual_start"].isoweekday() in days_of_week:
            values["rotation_virtual_start"] = get_start_time(
                values["rotation_virtual_start"], values
            )
            values["start"] = values["rotation_virtual_start"]
        elif values["everyday"] is True:
            values["rotation_virtual_start"] = get_start_time(
                values["rotation_virtual_start"], values
            )
            values["start"] = values["rotation_virtual_start"]
        else:
            # Calculate the next occurrence of this day from rotation_virtual_start
            current = values["rotation_virtual_start"]
            while current.isoweekday() not in days_of_week:
                current += timedelta(days=1)
            values["start"] = get_start_time(current, values)
        return values

    @root_validator
    def validate_start_and_end(cls, values):
        rotation_virtual_start = values.get("rotation_virtual_start")
        start = values.get("start")
        end = values.get("end")
        now = dt.now(timezone.utc)
        timezone_str = values.get("timezone")

        if isinstance(start, dt) and start.tzinfo is None:
            tz = pytz.timezone(timezone_str)
            start = tz.localize(start)

        if isinstance(end, dt) and end.tzinfo is None:
            tz = pytz.timezone(timezone_str)
            end = tz.localize(end)

        if start < now:
            raise ValueError("rotation start must be a future date")
        if not is_timezone_aware(start):
            raise ValueError("Rotation start must be a timezone aware datetime object")
        if not is_timezone_aware(rotation_virtual_start):
            raise ValueError(
                "rotation_virtual_start must be a timezone aware datetime object"
            )

        if end:
            if end < start:
                raise ValueError("rotation end must be after rotation start")
            if end < now:
                raise ValueError("rotation end must be a future date")
            if not is_timezone_aware(end):
                raise ValueError(
                    "Rotation start must be a timezone aware datetime object"
                )
        return values

    @root_validator
    def set_rotation_turn_length(cls, values):
        restrictions = values.get("restrictions", [])
        if restrictions:
            for restriction in restrictions:
                restriction_type = restriction.type
                if restriction_type == "daily_restriction":
                    values["rotation_turn_length_seconds"] = 86400
                elif restriction_type == "weekly_restriction":
                    values["rotation_turn_length_seconds"] = 604800
        return values


class Config(BaseModel):
    name: Optional[str] = Field(
        min_length=1, max_length=255, description="The schedule name"
    )
    description: Optional[str] = Field(
        max_length=1024, description="Schedule description"
    )
    timezone: str = Field(
        regex="^[\w/]+$",
        description=(
            "The schedule's timezone."
            " Timezones must be a valid timezone name as defined by datetime.tzname()."
        ),
    )

    @validator("timezone", pre=True)
    def validate_timezone(cls, v):
        # Replace spaces with underscores
        v = "/".join(substring.title() for substring in v.split("/"))
        v = v.replace(" ", "_")

        try:
            pytz.timezone(v)
            if not is_valid_timezone(v):
                raise ValueError(f"{v} is not a valid timezone supported by PagerDuty.")
        except pytz.UnknownTimeZoneError:
            raise ValueError(
                f"{v} is not a recognized timezone as defined by pytz.timezone"
            )
        return v
