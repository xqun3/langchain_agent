import logging
from langchain.memory import ConversationBufferMemory
from langchain_community.chat_models import ChatOpenAI
from langchain_community.llms import Bedrock
from langchain.prompts.chat import MessagesPlaceholder
from langchain.agents import AgentExecutor
from src.tools import (
    TOOLS_LIST,
    TOOLS_NAME,
    construct_format_tool_for_claude_prompt,
    create_xml_agent
    )
from confs import model_configs,model_back, SUFFIX, FORMAT_INSTRUCTIONS
from langchain.agents.structured_chat.base import StructuredChatAgent

import boto3
from langchain_community.chat_models import BedrockChat

from langchain_core.prompts.chat import ChatPromptTemplate

from langchain_community.chat_message_histories import (
    DynamoDBChatMessageHistory,
)
logger = logging.getLogger(__name__)

import boto3

# Get the service resource.
dynamodb = boto3.resource("dynamodb")

HUMAN_MESSAGE_TEMPLATE = "{input}\n\n{agent_scratchpad}"

def get_memory_db(session_id: str):
    """Get a conversation buffer with chathistory saved to dynamodb

    Returns:
        ConversationBufferMemory: A memory object with chat history saved to dynamodb
    """

    # Define the necessary components with the dynamodb endpoint
    message_history = DynamoDBChatMessageHistory(
        table_name="SessionTable",
        session_id=session_id,
        ttl=60*60, #seconds
    )
    logger.debug(message_history)

    memory = ConversationBufferMemory(
        memory_key="chat_history", 
        ai_prefix="AI", 
        human_prefix="User",
        chat_memory=message_history, 
        return_messages=True
    )

    return message_history, memory

class Invoice_Robot():
    def __init__(self,verbose=True):
        if model_back.startswith("claude3"):
            logger.debug("Using Bedrock runtime for Claude-3 Sonnet model")
            bedrock_runtime = boto3.client(
                service_name="bedrock-runtime",
                region_name="us-east-1",
            )

            logger.debug("model_config",model_configs)
            # model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
            model_id = model_configs["model_name"] 

            model_kwargs =  {
                "max_tokens": 2048,
                "temperature": 0,
                "top_k": 250,
                "top_p": 0.999,
                "stop_sequences": ["\n\nHuman"]
            }

            self.llm = BedrockChat(
                client=bedrock_runtime,
                model_id=model_id,
                model_kwargs=model_kwargs,
            )
            logger.debug(f"Bedrock runtime for Claude3 {model_configs['model_name']} model loaded successfully")

        else:
            boto3_bedrock = boto3.client(service_name='bedrock-runtime')
            self.llm = Bedrock(
                model_id=model_configs["model_name"],
                client=boto3_bedrock,
                model_kwargs={
                    'max_tokens_to_sample': model_configs["max_tokens_to_sample"],
                    "temperature": model_configs["temperature"]},
                streaming=False)

        tools_string = construct_format_tool_for_claude_prompt(TOOLS_LIST)


        
        # if input_variables is None:
        format_template = FORMAT_INSTRUCTIONS.format(tools_string=tools_string)
        system_prompt_template = "\n\n".join([format_template, SUFFIX])
        # input_variables = ["agent_scratchpad"]

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt_template),
                MessagesPlaceholder("chat_history", optional=True),
                ("human", HUMAN_MESSAGE_TEMPLATE),
            ]
        ) 

        self.agent = create_xml_agent(self.llm, TOOLS_LIST, prompt)

        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=TOOLS_LIST,
            return_intermediate_steps=True,
            verbose=verbose,
            stream=False,
            stop_sequence=["</function_result>", "</ask_user>", "</final_answer>"]
            )
    
    def get_response(self,
                     prompt: str,
                     session_id: str,
                     user_id: str
                     ) -> str:

        history, memory = get_memory_db(session_id) 
        chat_history = memory.load_memory_variables({})
        response = self.agent_executor.invoke({
            "input": prompt,
            "chat_history": chat_history["chat_history"]
        })

        logger.debug("\n!!!!!!!!!!!!!!!intermediate_steps!!!!!!!!!!!!!!!")
        logger.debug(response)
        response_output = response['output']
        action = response['intermediate_steps'][-1][0] if response['intermediate_steps'] else None
        tool_name = None
        tool_input = None
        logger.debug("*"*20)
        
        if action is not None:
            tool_name = action.tool
            tool_input = action.tool_input
            logger.debug(f"action", tool_name)
            # print(response['intermediate_steps'][-1][1]["retrieved_documents"])
        # if isinstance(response_output,dict) and action is not None and tool_name in FUNCTION_POST_LLM:
        #     llm_response = FUNCTION_POST_LLM[tool_name](response_output)
        #     display_response = FUNCTION_POST_DISPLAY[tool_name](response_output)
        if isinstance(response_output, str) and action is not None and tool_name == "knowledge_base_retrieve":
            # llm_response = FUNCTION_POST_LLM[tool_name](response_output)
            # retrieve_result = 
            # site_string = f"\n[{i}]"
            all_site_chunk_uris = "\nSites:"
            chunks = response['intermediate_steps'][-1][1]["retrieved_documents"]
            # print(type(chunks))
            for i, retrieve_chunk in enumerate(chunks):
                site_string = f'{" "*8}\n[{i+1}]:{retrieve_chunk["location"]["s3Location"]["uri"]}' 
                all_site_chunk_uris = "".join((all_site_chunk_uris, site_string))
            llm_response=str("".join((response_output,all_site_chunk_uris)))
            display_response = {"content": llm_response, "button": []}
        else:
            llm_response = str(response_output)
            display_response = {"content": llm_response, "button": []}

        is_call_function = tool_name in TOOLS_NAME and tool_name is not None

        history.add_user_message(prompt)
        history.add_ai_message(response_output)
        return {
            "content": llm_response,
            "button": display_response["button"],
            "function_name": tool_name if is_call_function else ""
        }

