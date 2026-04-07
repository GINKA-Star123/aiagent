from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
model = init_chat_model(
    model = "Qwen/Qwen3-8B",
    model_provider="openai",
    base_url="https://api.siliconflow.cn/v1/",
    api_key="sk-vzmnfbstebtisgwijxbbuwkbgpoxtonintojyigkqhcrfpyj",
    temperature=1,
    max_tokens = 2048
)


@tool
def get_weather(city:str) -> str:
    """
        获取指定位置的天气信息

        参数: 
            city:城市名称,如"北京","上海"
        
        返回:
            天气信息字符串
    """

    return "晴天,温度15°C"

agent = create_agent(
    model=model,
    tools =[get_weather],
    checkpointer=InMemorySaver()
)

config = { "configurable":{"thread_id":"conversation_1"}}

# 第一轮
agent.invoke(
    {"messages": [{"role": "user", "content": "我叫张三"}]},
    config=config
)

# 第二轮 - 记得第一轮！
response = agent.invoke(
    {"messages": [{"role": "user", "content": "我叫什么？"}]},
    config=config
)
# AI 会说"你叫张三"

print(response["messages"][-1].content)