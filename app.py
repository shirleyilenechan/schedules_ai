import json
import os
from dotenv import load_dotenv

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser, OutputFixingParser
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_openai import ChatOpenAI
 
import streamlit as st
from typing import List
import pandas as pd
from datetime import datetime, timedelta, timezone

import schedules_ai as sai
from example_prompt import system_message_prompt, system_message_requirements, system_message_info
from calendar_1 import dataframe_to_html_calendar

llm = ChatOpenAI()

class Response(BaseModel):
    message: str = Field(title="Message", description="The response message. If the user input includes all of the information required to create a schedule layer object, respond with Success. Otherwise, ask the user for to provide the missing information.")
    schedule_layer: List[sai.ScheduleLayers] = Field(description="A list of schedule layer objects")


def invoke_llm(user_input: str, message_history: list) -> Response:
    parser = PydanticOutputParser(pydantic_object=Response)
    fix_parser = OutputFixingParser.from_llm(parser=parser, llm=llm)

    format_instructions = f"Format instructions: {parser.get_format_instructions()}\n"
    prompt_messages = [SystemMessage(content=format_instructions)] + message_history + [HumanMessage(content=user_input)]
    prompt = ChatPromptTemplate.from_messages(prompt_messages)
    
    chain = prompt | llm | fix_parser
    response = chain.invoke({"input": user_input})
    parsed_response = Response.parse_obj(response)

    return parsed_response

def transform_schedule_to_df(layer):
    data = []
    user_sequence = [user.user_name for user in layer.users]
    restrictions = sorted(layer.restrictions, key=lambda x: (x.start_day_of_week, x.start_time_of_day))
    
    current_date = layer.start.date()
    end_date = current_date + timedelta(weeks=52)
    user_index = 0

    while current_date <= end_date:
        day_shifts = 0
        for restriction in restrictions:
            if current_date.isoweekday() == restriction.start_day_of_week:
                shift_start_time = datetime.combine(current_date, datetime.strptime(restriction.start_time_of_day, '%H:%M:%S').time(), tzinfo=layer.start.tzinfo)
                shift_end_time = shift_start_time + timedelta(seconds=restriction.duration_seconds)

                data.append({
                    'user': user_sequence[user_index],
                    'shift_start_datetime': shift_start_time,
                    'shift_end_datetime': shift_end_time,
                    'shift_duration': shift_end_time - shift_start_time
                })
                day_shifts += 1

        # Only increment the user index if there were shifts this day
        if day_shifts > 0:
            user_index = (user_index + 1) % len(user_sequence)

        # Move to the next day
        current_date += timedelta(days=1)

    df = pd.DataFrame(data)
    df_sorted = df.sort_values(by=['shift_start_datetime'])
    print(df_sorted.to_string())
    return df_sorted
   
def main():
    st.set_page_config(page_title="Schedule Config", layout="wide")
    st.title("Configure Your Schedule Rotation 🗓️")

    if "config" not in st.session_state:
        st.session_state.config = []

    if "messages" not in st.session_state:
        st.session_state.messages = [SystemMessage(content=system_message_prompt), SystemMessage(content=system_message_requirements), 
                                     SystemMessage(content=system_message_info)]
    if "schedule_layer" not in st.session_state:
        st.session_state.schedule_layer = [{}]

    st.session_state.json_complete = False
    schedule_info, schedule_rotation = st.tabs(["Schedule Info", "Schedule Rotation"])
    
    with schedule_info:        
        with st.form(key='config_form'):
            name = st.text_input("Schedule Name")
            description = st.text_area("Schedule Description")
            timezone = st.selectbox(
                label='Select a PagerDuty Supported Timezone',
                options=sai.get_pagerduty_supported_timezones(),
                index=None
            )
            submit_button = st.form_submit_button(label='Submit')

        if submit_button:
            config_obj = sai.Config(name=name, description=description, timezone=timezone)
            st.session_state.config.append(HumanMessage(content=config_obj.json()))
            st.chat_message("assistant").write(f"Thank you for submitting that information!  \n\nHere is the input I received: {config_obj.json()}.  \n\nIf this is incorrect, please re-submit the information above. Otherwise, please proceed to the Schedule Rotation tab.")
            st.session_state.config_submitted = True

    if st.session_state.get("config_submitted", False):
        with schedule_rotation:
            col1, col2 = st.columns([0.5, 0.5])
            with col1:
                messages = st.container()
                user_input = st.chat_input(key="rotation_input")
                with messages:
                    for msg in st.session_state.messages:
                        if isinstance(msg, HumanMessage):
                            st.chat_message("user").write(msg.content)
                        elif isinstance(msg, AIMessage):
                            st.chat_message("assistant").write(msg.content)
                    if not st.session_state.json_complete:
                        if user_input:
                            st.session_state.messages.append(HumanMessage(content=user_input))
                            st.chat_message("user").write(user_input)
                            st.chat_message("assistant").write("One moment while I attempt to create the schedule layers please") 
                            response = invoke_llm(user_input, st.session_state.messages)
                            if "Success" in response.message:
                                st.chat_message("assistant").write(f"Here is the list of validated schedule layer objects: {response.schedule_layer}")
                                st.session_state.schedule_layer = response.schedule_layer
                                st.session_state.json_complete = True
                            else:
                                st.session_state.messages.append(AIMessage(content=response.message))
                                st.chat_message("assistant").write(response.message)
            with col2:
                schedule_layers = st.session_state.schedule_layer
                for layer in schedule_layers: 
                    shifts_df = transform_schedule_to_df(layer)
                    if not shifts_df.empty:
                        # Convert to HTML
                        html_calendar = dataframe_to_html_calendar(shifts_df)
                        # Display the HTML calendar in Streamlit
                        st.markdown(html_calendar, unsafe_allow_html=True)
                    else:
                        st.write("No shift data available.")

if __name__ == "__main__":
    main()