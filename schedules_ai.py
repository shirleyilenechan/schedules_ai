import re
import requests
import os
from dateutil import parser

from datetime import datetime as dt, tzinfo, timezone, timedelta
from langchain_core.pydantic_v1 import BaseModel, Field, validator, root_validator, conint
from typing import Optional, Dict, List, Literal

import pytz
from pytz import timezone as pytz_timezone
from icalendar import Calendar
import pd_timezones


def is_valid_timezone(tz_identifier, timezones):
        pd_tz = pd_timezones.timezones
        # Check if the provided tz_identifier is in the list of valid timezones
        if tz_identifier in pd_tz:
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
    
    @validator('start_time_of_day', pre=True)
    def validate_start_time(cls, v: str):
        # Attempt to parse the string into a datetime object then convert to time
        try:
            dt.strptime(v, '%H:%M:%S').time()
        except ValueError:
            raise ValueError(f'{v} is not a valid time')
        # Since the field expects a string, convert the time object back to string
        return v

    @validator('start_day_of_week', pre=True)
    def validate_isoweekday(cls, v):
        if not 1 <= v <= 7:
            raise ValueError(f'{v} is not a valid iso weekday')
        return v

class ScheduleLayers(BaseModel):
    timezone: str = Field(regex = '^[\w/]+$', description="The timezone for a group of users. Timezones must be a valid timezone name as defined by datetime.tzname().")
    start: dt = Field(description="The group start provided by the user, represented as a datetime object. start must be timezone aware. start must also be a future date.")
    rotation_virtual_start: dt = Field(description="The group start provided by the user, represented as a datetime object. rotation_virtual_start must be timezone aware. rotation_virtual_start must also be a future date.")
    end: Optional[dt] = Field(default=None, description="The end date and time for a group of users, represented as a datetime object. End must be timezone aware. If provided, the end date must also be a future date.")
    rotation_turn_length_seconds: Literal[86400, 604800] = Field(description="If the group restriction is a daily_restriction, then the value is 86400. If the group restriction is a weekly_restriction then the value is 604800")
    users: List[User] = Field(description = "A list of user objects, representing each user in the group. The list should match the group's rotation order and rotation pattern exactly.")
    restrictions: List[Restriction] = Field(description = "A list of restriction objects for the group.")


    @root_validator
    def validate_start_and_end(cls, values):
        tz = values.get('timezone')
        rotation_virtual_start = values.get('rotation_virtual_start')
        start = values.get('start')
        end = values.get('end')
        now = dt.now(timezone.utc)
        
        if start < now:
            raise ValueError("rotation start must be a future date")
        if not is_timezone_aware(start):
            raise ValueError("Rotation start must be a timezone aware datetime object")
        if not is_timezone_aware(rotation_virtual_start):
            raise ValueError("rotation_virtual_start must be a timezone aware datetime object")
        
    
        if end:
            if end < start:
                raise ValueError("rotation end must be after rotation start")
            if end < now:
                raise ValueError("rotation end must be a future date")
            if not is_timezone_aware(end):
                raise ValueError("Rotation start must be a timezone aware datetime object")
        return values

    @root_validator
    def adjust_start_date(cls, values):
        if not values["restrictions"]:
            return

        # Find the minimum start_day_of_week
        min_day = min(r.start_day_of_week for r in values['restrictions'])

        # If rotation_virtual_start is already on the correct day, use it
        if values['rotation_virtual_start'].isoweekday() == min_day:
            values['start'] = values['rotation_virtual_start']
        else:
            # Calculate the next occurrence of this day from rotation_virtual_start
            current = values['rotation_virtual_start']
            while current.isoweekday() != min_day:
                current += timedelta(days=1)
            values['start'] = current
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

        timezones = pd_timezones.timezones

        try:
            pytz.timezone(v)
            if not is_valid_timezone(v, timezones):
                raise ValueError(f'{v} is not a valid timezone supported by PagerDuty.')
        except pytz.UnknownTimeZoneError:
            raise ValueError(f'{v} is not a recognized timezone as defined by pytz.timezone')
        return v