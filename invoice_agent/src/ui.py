import streamlit as st
from PIL import Image
import json
import logging
import boto3
import sys
import uuid
import time
from pathlib import Path
path = Path(__file__)
parrent_path = path.parent.parent
sys.path.insert(0, parrent_path)
from src.core_xml_agent3_dynamodb import Invoice_Robot
is_clear_memory = True 
streaming = True
user_id = "000001"
verbose = False
robot = Invoice_Robot(verbose=verbose)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

st.set_page_config(page_title="Invoice Agent", page_icon="♊")


REGION = "us-east-1"

agent_id = ""
agent_alias_id = ""

def bedrock_agent():
    credentials = boto3.Session().get_credentials()
    region = REGION
    aws_access_key_id = credentials.access_key # you can modify to your access_key 
    aws_secret_access_key = credentials.secret_key  # you can modify to your secret_key 
    client = boto3.client("bedrock-agent-runtime", region_name=region, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
    return client

client = bedrock_agent()
def invoke(client, question: str, sessionid: str, agent_id: str, agent_alias_id: str, enable_trace=False):
    final_answer = ""
    response = client.invoke_agent(
        inputText=question, # 输入文本
        agentId=agent_id,  # 创建的 Agent 的 ID
        agentAliasId=agent_alias_id, # 创建的 Agent alias id
        sessionId=sessionid, # 当前会话的session id
        enableTrace=enable_trace # 是否打开 trace
    )
    event_stream = response['completion']
    try:
        for event in event_stream:        
            # print(event)
            if 'chunk' in event:
                data = event['chunk']['bytes']
                final_answer = data.decode('utf8')
                logger.info(f"Final answer ->\n{final_answer}") 
                end_event_received = True
                # End event indicates that the request finished successfully
            elif 'trace' in event:
                trace = event['trace']
                logger.info(json.dumps(event['trace'], indent=2, ensure_ascii=False))
            else:
                raise Exception("unexpected event.", event)
    except Exception as e:
        raise Exception("unexpected event.", e)
    
    return final_answer


st.title("发票助手")


if "messages" not in st.session_state:
    st.session_state["messages"] = []

if "session_id" not in st.session_state:
    st.session_state["session_id"] = str(uuid.uuid4())

with st.sidebar:
    option = st.selectbox('选择Agent实现方式',('bedrock-agent-claudev2', 'bedrock-fc-claude3-sonnet'))

    if 'model' not in st.session_state or st.session_state.model != option:
        # st.session_state.chat = invoke
        st.session_state.model = option
        
        st.session_state.messages.clear()
        st.session_state["messages"] = []
        # st.session_state.session_id.clear()
        st.session_state["session_id"] = str(uuid.uuid4())

    st.divider()
    st.markdown("""<span ><font size=1>与我联系</font></span>""", unsafe_allow_html=True)

    "[GitHub](https://github.com/xiaoqunnaws/bedrock_agent_knowledege_base/tree/main)"
    
    st.divider()


    if st.button("清除聊天历史"):
        st.session_state.messages.clear()
        st.session_state["messages"] = []
        # st.session_state.session_id.clear()
        st.session_state["session_id"] = str(uuid.uuid4())

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input():
    
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)
        # timer = st.empty()
        # response=st.session_state.messages.append({"role": "user", "content": prompt})
    with st.spinner('Wait for it...'):
        start_time = time.perf_counter()
        if st.session_state.model == "bedrock-agent-claudev2":
            response = invoke(
                    client,
                    prompt,
                    st.session_state["session_id"],
                    agent_id,
                    agent_alias_id,
                    enable_trace=False
                )
        elif st.session_state.model == "bedrock-fc-claude3-sonnet":

            res = robot.get_response(
                prompt=prompt,
                session_id=st.session_state["session_id"],
                user_id=user_id
            )
            # print(res["content"])
            response = res["content"]
        end_time = time.perf_counter()
        ss = end_time - start_time
    with st.chat_message("assistant"):
        st.markdown(response)
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.success(f"{ss:.2f}s")