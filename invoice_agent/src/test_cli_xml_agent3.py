import os
import sys
import uuid
import json
root_dir = None
dir_name_0 = os.path.basename(os.path.dirname(os.path.abspath(sys.argv[0])))
if dir_name_0 == 'src':
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0])))
else:
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
sys.path.insert(0, root_dir)
from src.core_xml_agent3_dynamodb import Invoice_Robot
is_clear_memory = True 
streaming = True
session_id = str(uuid.uuid4())
user_id = "000002"
verbose = True
robot = Invoice_Robot(verbose=verbose)
if __name__ == "__main__":
    print(f"使用session id: {session_id}")
    while True:
        question = input("User:")
        print(json.dumps(question))
        if question.strip() == "stop":
            break
        print("Assistant:",end="")
        res = robot.get_response(
            prompt=question,
            session_id=session_id,
            user_id=user_id
        )
        print(res["content"])
    # if is_clear_memory:
    #     res["history"].clear()
