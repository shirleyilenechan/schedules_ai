from langchain.output_parsers import PydanticOutputParser, OutputFixingParser
from langchain.prompts import PromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field, validator, root_validator, conint
from langchain_openai import ChatOpenAI

import re
import requests

from dateutil import parser

from datetime import datetime as dt, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from typing import Optional, Dict, List, Literal

from example_prompt import example_good_input, example_good_response


def get_valid_timezones():
    # XHR request to GET the documentation from this URL
    url = 'https://stoplight.io/api/v1/projects/cHJqOjU5NTYx/nodes/1afe25e9c94cb-types'
    response = requests.get(url).json()
    # extract the timezone section of the documentation
    timezone_section_pattern = r'### Time Zone\n\n(.*?)(\n###|$)'

    valid_timezones = re.search(timezone_section_pattern, response['data'], re.DOTALL)

    return valid_timezones


def is_valid_timezone(tz_identifier):
     # timezone identifier regex pattern
    pattern = r'\|\s*([\w/]+)\s*\|'
    valid_timezones = get_valid_timezones()

    if valid_timezones:
        # Extract the matched timezone section as a string
        timezone_string = valid_timezones.group(0)
        
        # Use re.findall() to create a list of all matches for the timezone identifier pattern
        timezones = re.findall(pattern, timezone_string, re.DOTALL)

        if not timezones:
            return False
        else: 
            return True
        

def is_timezone_aware(date_time):
    return date_time.tzinfo is not None


class User(BaseModel):
    user_initials: str = Field(max_length=4, regex = '^[A-Za-z0-9]+$', description = "2 to 4 characters, representing the user's initials")
    type: Literal['user_reference'] = Field(description = "The value in this field should always be 'user_reference'")


class Restriction(BaseModel):
    type: Literal['daily_restriction', 'weekly_restriction'] = Field(description = "For each shift throughout the week, check which user works each shift. If it is the same user for each shift then that week will be considered a weekly_shift. If every week is a weekly_shift, then the value is 'weekly_restriction'")
    duration_seconds: conint(gt=0) = Field(description = "Time delta between the shift start and shift end, measured in seconds")
    start_time_of_day: str = Field(regex = '^([01]?[0-9]|2[0-3]):([0-5]?[0-9]):([0-5]?[0-9])$', description = "Start time for start_day_of_week reprsented as a string in HH:mm:ss format")
    start_day_of_week: int = Field(description = "Day of the week the shift occurs, represented in ISO 8601 day format (1 is Monday)")
    start_dt: dt = Field(description = "a datetime object, representing the first occurrence of the start_day_of_week")
    
    @validator('start_time_of_day', pre=True)
    def validate_time_format(cls, v: str):
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
    start: dt = Field(description = "The rotation start date and time, represented as a datetime object. Start should be represented in the schedule's timezone. Example format: dt(2024, 4, 29, 9, 0, tzinfo=ZoneInfo(key='America/Los_Angeles'))")
    rotation_virtual_start: dt = Field(description = "This datetime object should match the rotation_start datetime object exactly, including the timezone information")
    end: Optional[dt] = Field(default=None, description="The rotation end date and time, represented as a datetime object. End should be represented in the schedule's timezone. If no end date is provided, the default should be null")
    rotation_turn_length_seconds: Literal[86400, 604800] = Field(description="If the group restrictions are daily_restrictions, then the value is 86400. If the group restrictions are weekly_restrictions then the value is 604800")
    users: List[User] = Field(description = "An ordered list of users, matching the rotation pattern exactly. The list should include all instances where they appear in the rotation pattern. For example if PB, DS, DS, BV is the rotation pattern, then two DS user objects should be added to the user list between PB and BV.")
    restrictions: List[Restriction] = Field(description = "A list of restriction objects.")


    @root_validator
    def validate_start_and_end(cls, values):
        start = values.get('start')
        rotation_start = values.get('rotation_virtual_start')
        end = values.get('end')
        now = dt.now(start.tzinfo)
        
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
    name: str = Field(min_length=1, max_length=255, description ="The schedule name")
    description: str = Field(max_length=1024, description ="Schedule description")
    timezone: str = Field(regex = '^[\w/]+$', description="The schedule's timezone. Must be a valid time zone identifer as listed here: https://developer.pagerduty.com/docs/1afe25e9c94cb-types#time-zone. All datetime objects throughout the schedule should be synced to this timezone")
    schedule_layers: List[ScheduleLayers] = Field(description = "A list of schedule layer objects, representing each shift group. For example, if the schedule contains Group A and Group B, then the list should contain 2 schedule objects")
    
    @validator('timezone', pre=True)
    def validate_timezone(cls, v):
        if not is_valid_timezone(v):
            raise ValueError(f'{v} is not a valid timezone supported by PagerDuty.')
        try:
            ZoneInfo(v)
        except ZoneInfoNotFoundError:
            raise ValueError(f'{v} is not a recognized timezone identifier.')
        return v


    @root_validator
    def adjust_layer_timezones(cls, values):
        tzinfo = ZoneInfo(values.get('timezone'))
        for layer in values.get('schedule_layers', []):
            if layer.start:
                layer.start = layer.start.astimezone(tzinfo)
            if layer.rotation_virtual_start:
                layer.rotation_virtual_start = layer.rotation_virtual_start.astimezone(tzinfo)
            if layer.end:
                layer.end = layer.end.astimezone(tzinfo)

            for restriction in layer.restrictions:
                if isinstance(restriction, str):
                    restriction.start_dt = parser.parse(restriction.start_dt)
                restriction.start_dt = restriction.start_dt.astimezone(tzinfo)
                restriction.start_time_of_day = restriction.start_dt.strftime('%H:%M:%S')
        return values