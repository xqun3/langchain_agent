
import re
from typing import Union
import xmltodict
import logging
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.exceptions import OutputParserException
from langchain.agents import AgentOutputParser

import sys
logger = logging.getLogger(__name__)
def str_to_class(classname):
    return getattr(sys.modules["src.tools.functions"], classname)

FUNCTION_CALL_PATTERN = r"<function_calls>(.*?)</function_calls>"
CALL_FUNCTION_TAG= r"<call_function_tag>(.*?)</call_function_tag>"

def parse_function_call(text: str):
    text = f"{text.strip()}</function_calls>"
    func_str = re.search(FUNCTION_CALL_PATTERN, text, re.DOTALL).group(1)
    logger.debug("func_str: ", func_str)
    func_call_dict = xmltodict.parse(func_str)
    logger.debug("func_call_dict: ", func_call_dict)

    func_name = func_call_dict['invoke']['tool_name']
    parameters = func_call_dict['invoke']['parameters']
    return func_name, parameters

class XMLAgentOutputParser(AgentOutputParser):
    """Parses tool invocations and final answers in XML format.

    Expects output to be in one of two formats.

    If the output signals that an action should be taken,
    should be in the below format. This will result in an AgentAction
    being returned.

    ```
    <tool>search</tool>
    <tool_input>what is 2 + 2</tool_input>
    ```

    If the output signals that a final answer should be given,
    should be in the below format. This will result in an AgentFinish
    being returned.

    ```
    <final_answer>Foo</final_answer>
    ```
    """
    
    def parse(self, text: str) -> Union[AgentAction, AgentFinish]:
        # logger.debug("parse HERE!!!!!")
        try:
            if "<ask_user>" in text:
                if "<function_calls>" not in text:
                    ask_user_text = text.replace("<ask_user>", "")
                    ask_user_text = ask_user_text.replace("</ask_user>", "")
                    return AgentFinish(return_values={"output": ask_user_text}, log=text)
                else:

                    func_name, parameters = parse_function_call(text)
                    return AgentAction(tool=func_name, tool_input=parameters, log=text)
            elif "<function_calls>" in text:
                func_name, parameters = parse_function_call(text)

                return AgentAction(tool=func_name, tool_input=parameters, log=text)
            
            elif "<final_answer>" in text:
                _, answer = text.split("<final_answer>")
                if "</final_answer>" in answer:
                    answer = answer.split("</final_answer>")[0]
                if answer == "":
                    answer = _
                return AgentFinish(return_values={"output": answer}, log=text)
            else:
                # logger.debug("text:", text)
                return AgentFinish({"output": text}, text)
        except Exception as e:
            raise OutputParserException(f"Could not parse LLM output: {text}") from e

    def get_format_instructions(self) -> str:
        raise NotImplementedError

    @property
    def _type(self) -> str:
        return "xml-agent"