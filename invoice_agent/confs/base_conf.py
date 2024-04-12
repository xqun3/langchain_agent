
# llm 设置
model_back = "claude3-sonnet"
# model_back = "claude3-haiku"
# model_back = "claude"
model_configs = {
    "claude":
        {
            "model_name":"anthropic.claude-v2",
            "max_tokens_to_sample":2000,
            "temperature": 0.5
        },
    "claude3-sonnet":
        {
            "model_name":"anthropic.claude-3-sonnet-20240229-v1:0",
            "max_tokens_to_sample":2000,
            "temperature": 0.5
        },
    "claude3-haiku":
        {
            "model_name":"anthropic.claude-3-haiku-20240307-v1:0",
            "max_tokens_to_sample":2000,
            "temperature": 0.5
        }
}
