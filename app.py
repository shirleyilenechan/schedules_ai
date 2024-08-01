from datetime import datetime, timedelta
from typing import List

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from langchain.output_parsers import OutputFixingParser, PydanticOutputParser
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_openai import ChatOpenAI

import pd_timezones
import schedules_ai as sai
from calendar_1 import dataframe_to_html_calendar
from system_prompts import SYSTEM_MESSAGE

load_dotenv()
llm = ChatOpenAI(
    model="gpt-3.5-turbo", model_kwargs={"response_format": {"type": "json_object"}}
)


class Response(BaseModel):
    message: str = Field(description="The response message.")
    schedule_layer: List[sai.ScheduleLayers] | None = Field(
        default=[],
        description="list of ScheduleLayer objects",
    )


def invoke_llm(user_input: str, message_history: list) -> Response:
    parser = PydanticOutputParser(pydantic_object=Response)
    fix_parser = OutputFixingParser.from_llm(parser=parser, llm=llm)  # type: ignore
    format_instructions = f"Format instructions: {parser.get_format_instructions()}."
    system_message = message_history[0].content + format_instructions.replace(
        "{", "{{"
    ).replace("}", "}}")
    prompt_messages = (
        [SystemMessage(content=system_message)]
        + message_history[1:]
        + [HumanMessage(content=user_input)]
    )
    prompt = ChatPromptTemplate.from_messages(prompt_messages)

    response = (prompt | llm | fix_parser).invoke({})

    return response


def transform_schedule_to_df(layers):
    data = []
    for layer in layers:
        if isinstance(layer, sai.ScheduleLayers):
            user_sequence = [user.user_name for user in layer.users]
            restrictions = layer.restrictions

            current_date = layer.start.date()
            end_date = current_date + timedelta(weeks=52)
            user_index = 0

            while current_date <= end_date:
                for restriction in restrictions:
                    if current_date.isoweekday() == restriction.start_day_of_week:
                        shift_start_time = datetime.combine(
                            current_date,
                            datetime.strptime(
                                restriction.start_time_of_day, "%H:%M:%S"
                            ).time(),
                        ).replace(
                            tzinfo=layer.start.tzinfo
                        )  # Ensure timezone is set
                        shift_end_time = shift_start_time + timedelta(
                            seconds=restriction.duration_seconds
                        )

                        data.append(
                            {
                                "user": user_sequence[user_index],
                                "shift_start_datetime": shift_start_time,
                                "shift_end_datetime": shift_end_time,
                                "shift_duration": shift_end_time - shift_start_time,
                            }
                        )

                        if restriction.type == "daily_restriction":
                            user_index = (user_index + 1) % len(user_sequence)
                if (
                    restriction.type == "weekly_restriction"
                    and current_date.weekday() == 6
                ):  # End of the week
                    user_index = (user_index + 1) % len(user_sequence)

                current_date += timedelta(days=1)

    if not data:  # If no data was added, return an empty DataFrame
        return pd.DataFrame()

    df = pd.DataFrame(data)
    df_sorted = df.sort_values(by=["shift_start_datetime"])
    return df_sorted


def process_user_input(user_input):
    st.session_state.messages.append(HumanMessage(content=user_input))
    st.chat_message("user").write(user_input)
    confirmation = "One moment while I attempt to create the schedule layers please"
    st.chat_message("assistant").write(confirmation)
    st.session_state.messages.append(AIMessage(content=confirmation))
    response = invoke_llm(user_input, st.session_state.messages)

    if "Success" in response.message:
        st.session_state.schedule_layer.extend(response.schedule_layer)
        validated = (
            "Here is the list of validated schedule layer objects: "
            f"{st.session_state.schedule_layer}"
        )
        st.chat_message("assistant").write(validated)
        st.session_state.messages.append(AIMessage(content=validated))
        add_another = (
            "⏰ To add another group to the schedule, please tell me about "
            "the group and describe their shifts below."
        )
        st.chat_message("assistant").write(add_another)
        st.session_state.messages.append(AIMessage(content=add_another))
    else:
        st.session_state.messages.append(AIMessage(content=response.message))
        st.chat_message("assistant").write(response.message)


def main():
    st.set_page_config(page_title="Schedule Config", layout="wide")
    st.title("Configure Your Schedule Rotation 🗓️")

    if "config" not in st.session_state:
        st.session_state.config = ""

    if "timezone" not in st.session_state:
        st.session_state.timezone = ""

    if "schedule_name" not in st.session_state:
        st.session_state.schedule_name = ""

    if "messages" not in st.session_state:
        st.session_state.messages = [SystemMessage(content=SYSTEM_MESSAGE)]
    if "schedule_layer" not in st.session_state:
        st.session_state.schedule_layer = []

    st.session_state.json_complete = False
    schedule_info, schedule_rotation = st.tabs(["Schedule Info", "Schedule Rotation"])

    with schedule_info:
        with st.form(key="config_form"):
            name = st.text_input("Schedule Name")
            description = st.text_area("Schedule Description")
            timezone = st.selectbox(
                label="Select a PagerDuty Supported Timezone",
                options=pd_timezones.timezones,
                index=None,
            )
            submit_button = st.form_submit_button(label="Submit")

        if submit_button:
            config_obj = sai.Config(
                name=name, description=description, timezone=timezone
            )
            st.session_state.config = (
                "Thank you for submitting that information!\n\n "
                f"Here is the input I received: {config_obj.json()}.\n\n "
                "If this is incorrect, please re-submit the information above. "
                "Otherwise, please proceed to the Schedule Rotation tab."
            )
            st.session_state.timezone = timezone
            st.session_state.schedule_name = name
            st.session_state.config_submitted = True

        # Display the assistant message if it exists
        if st.session_state.config:
            st.chat_message("assistant").write(st.session_state.config)

    if st.session_state.get("config_submitted", False):
        with schedule_rotation:
            col1, col2 = st.columns([0.5, 0.5])
            with col1:
                messages = st.container()
                user_input = st.chat_input(key="rotation_input")

                # Initial greeting if no messages exist
                if len(st.session_state.messages) == 1:  # Only system messages
                    initial_greeting = (
                        "Hello 👋, I am the PagerDuty schedule bot! "
                        "Please tell me about the first group, "
                        "and the shifts they work."
                    )
                    st.session_state.messages.append(
                        AIMessage(content=initial_greeting)
                    )

                with messages:
                    for msg in st.session_state.messages:
                        if isinstance(msg, HumanMessage):
                            st.chat_message("user").write(msg.content)
                        elif isinstance(msg, AIMessage):
                            st.chat_message("assistant").write(msg.content)

                    if user_input:
                        process_user_input(user_input)
            with col2:
                # Display schedule name and timezone
                st.subheader("Schedule Information")
                st.write(f"**Schedule Name:** {st.session_state.schedule_name}")
                st.write(f"**Timezone:** {st.session_state.timezone}")
                schedule_layers = st.session_state.schedule_layer
                shifts_df = transform_schedule_to_df(schedule_layers)
                if not shifts_df.empty:
                    # Convert to HTML
                    html_calendar = dataframe_to_html_calendar(
                        shifts_df, st.session_state.timezone
                    )
                    # Display the HTML calendar in Streamlit
                    st.markdown(html_calendar, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
