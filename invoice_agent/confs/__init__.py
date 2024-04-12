import os
from confs.base_conf import *
from confs.system_prompt import *
#设置prompt语言
# SYSTEM_PROMPT = system_prompt

# 配置更新
model_configs = model_configs[model_back]
# 设置 log路径
logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir, exist_ok=True)

