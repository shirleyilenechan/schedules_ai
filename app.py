import os
from dotenv import load_dotenv

from langchain_community.chat_message_histories import StreamlitChatMessageHistory
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, HumanMessagePromptTemplate
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.output_parsers import PydanticOutputParser, OutputFixingParser
from langchain_openai import ChatOpenAI

from datetime import datetime as dt
import streamlit as st

import schedules_ai as sai
from example_prompt import example_good_input, example_good_response

load_dotenv()

def main():

    st.set_page_config(page_title="Schedule Config", layout="wide")
    st.title("Configure Your Schedule Rotation 🗓️")

    name = st.text_input("Schedule Name", "Ballchan")
    description = st.text_area("Description", "Rotation schedule for Shirley and Kevin")
    timezone = st.text_input("Schedule Timezone", "US Pacific")

    system_message = (
        "You are an AI chatbot that will take in a prompt from the user.\n"
        "You will use the information in the prompt to generate a schedule object for the POST request to https://api.pagerduty.com/schedules.\n"
        "NOTE: all datetime objects must be timezone aware\n"
        f"Today is {dt.now().strftime('%A, %B %d, %Y')}.\n"
        f"Below is an EXAMPLE of a good prompt and response for reference only:\n"
        f"Prompt:\n{example_good_input}\n"
        f"Response:\n{example_good_response}\n"
    )
    system_message = SystemMessage(content=system_message)

    if "messages" not in st.session_state:
        st.session_state["messages"] = [AIMessage(content="Hello! I would be glad to help you set up your on-call schedule! To start tell me about the first group and their shifts.")]
    
    if prompt := st.chat_input():
        human_input = (
            f"The schedule name is: {name}."
            f" The schedule description is: {description}."
            f" The schedule timezone: {timezone}.\n"
            f"{prompt}"
        )
        human_input = HumanMessage(content=human_input)

        prompt_template = ChatPromptTemplate.from_messages(
            [system_message, *st.session_state["messages"], human_input]
        )

        parser = PydanticOutputParser(pydantic_object=sai.Config)
        fix_parser = OutputFixingParser.from_llm(parser=parser, llm=ChatOpenAI())

        llm = ChatOpenAI()
        chain = prompt_template | llm | fix_parser
            
        # If user inputs a new prompt, generate and draw a new response

        st.chat_message("human").write(prompt)
        response = chain.invoke({})
        st.chat_message("ai").json(response.json())
    


if __name__ == "__main__":
    main()
