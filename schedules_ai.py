import re
import requests
import os
from dateutil import parser

from datetime import datetime as dt, tzinfo, timezone
from langchain_core.pydantic_v1 import BaseModel, Field, validator, root_validator, conint
from typing import Optional, Dict, List, Literal

import pytz
from icalendar import Calendar
from datetime import datetime as dt


def get_pagerduty_supported_timezones():
    # XHR request to GET the documentation from this URL
    url = 'https://stoplight.io/api/v1/projects/cHJqOjU5NTYx/nodes/1afe25e9c94cb-types'
    response = requests.get(url).json()
    # extract the timezone section of the documentation
    timezone_section_pattern = r'### Time Zone\n\n(.*?)(\n###|$)'

    valid_timezones = re.search(timezone_section_pattern, response['data'], re.DOTALL)

    # timezone identifier regex pattern
    pattern = r'\|\s*([\w/]+)\s*\|'

    if valid_timezones:
        # Extract the matched timezone section as a string
        timezone_string = valid_timezones.group(0)
        
        # Use re.findall() to create a list of all matches for the timezone identifier pattern
        timezones = re.findall(pattern, timezone_string, re.DOTALL)

    return timezones[1:]

def is_valid_timezone(tz_identifier, timezones):
        # Check if the provided tz_identifier is in the list of valid timezones
        if tz_identifier in timezones:
            return True
        else:
            return False

def is_timezone_aware(date_time):
    return tzinfo is not None

class User(BaseModel):
    user_name: str = Field(description = "The names of the users in the group")
    type: Literal['user_reference'] = Field(description = "The value in this field should always be 'user_reference'")


class Restriction(BaseModel):
    type: Literal['daily_restriction', 'weekly_restriction'] = Field(description = "For each week, check which user(s) work during the week. If the same user works all of the shifts that week, that week is considered a weekly_shift. If every week is a weekly_shift, then the value is weekly_restriction")
    duration_seconds: conint(gt=0) = Field(description = "Time delta between shift start - shift end, measured in seconds")
    start_time_of_day: str = Field(regex = '^([01]?[0-9]|2[0-3]):([0-5]?[0-9]):([0-5]?[0-9])$', description = "Start time for start_day_of_week reprsented as a string in HH:mm:ss format")
    start_day_of_week: int = Field(description = "Day of the week the shift occurs, represented in ISO 8601 day format (1 is Monday)")
    
    @validator('start_time_of_day', pre=True, allow_reuse = True)
    def validate_start_time(cls, v: str):
        # Attempt to parse the string into a datetime object then convert to time
        try:
            dt.strptime(v, '%H:%M:%S').time()
        except ValueError:
            raise ValueError(f'{v} is not a valid time')
        # Since the field expects a string, convert the time object back to string
        return v

    @validator('start_day_of_week', pre=True, allow_reuse = True)
    def validate_isoweekday(cls, v):
        if not 1 <= v <= 7:
            raise ValueError(f'{v} is not a valid iso weekday')
        return v

class ScheduleLayers(BaseModel):
    timezone: str = Field(regex = '^[\w/]+$', description="The timezone for a group of users. Timezones must be a valid timezone name as defined by datetime.tzname().")
    start: dt = Field(description = "The start date and time for a group of users, represented as a datetime object. Start must be timezone aware. Start must also be a future date.")
    rotation_virtual_start: dt = Field(description = "Datetime object, matching the start datetime object exactly, including the timezone.")
    end: Optional[dt] = Field(default=None, description="The end date and time for a group of users, represented as a datetime object. End must be timezone aware. If provided, the end date must also be a future date.")
    rotation_turn_length_seconds: Literal[86400, 604800] = Field(description="If the group restriction is a daily_restriction, then the value is 86400. If the group restriction is a weekly_restriction then the value is 604800")
    users: List[User] = Field(description = "A list of user objects, representing each user in the group. The list should match the group's rotation order and rotation pattern exactly.")
    restrictions: List[Restriction] = Field(description = "A list of restriction objects for the group.")


    @root_validator
    def validate_start_and_end(cls, values):
        start = values.get('start')
        rotation_start = values.get('rotation_virtual_start')
        end = values.get('end')
        now = dt.now(timezone.utc)
        
        if start != rotation_start:
            raise ValueError(f"rotation virtual start must match start")
        if start < now:
            raise ValueError("rotation start must be a future date")
        if not is_timezone_aware(start):
            raise ValueError("Rotation start must be a timezone aware datetime object")
    
        if end:
            if end < start:
                raise ValueError("rotation end must be after rotation start")
            if end < now:
                raise ValueError("rotation end must be a future date")
            if not is_timezone_aware(end):
                raise ValueError("Rotation start must be a timezone aware datetime object")
        return values

class Config(BaseModel):
    name: Optional[str] = Field(min_length=1, max_length=255, description ="The schedule name")
    description: Optional[str] = Field(max_length=1024, description ="Schedule description")
    timezone: str = Field(regex = '^[\w/]+$', description="The schedule's timezone. Timezones must be a valid timezone name as defined by datetime.tzname().")
    
    @validator('timezone', pre=True)
    def validate_timezone(cls, v):
        # Replace spaces with underscores
        v = '/'.join(substring.title() for substring in v.split('/'))
        v = v.replace(' ', '_')

        timezones = get_pagerduty_supported_timezones()

        try:
            pytz.timezone(v)
            if not is_valid_timezone(v, timezones):
                raise ValueError(f'{v} is not a valid timezone supported by PagerDuty.')
        except pytz.UnknownTimeZoneError:
            raise ValueError(f'{v} is not a recognized timezone as defined by pytz.timezone')
        return v
