from langchain.llms import OpenAI
from langchain.agents import load_tools, initialize_agent
import os

os.environ["OPENAI_API_KEY"] = "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"
os.environ["SERPAPI_API_KEY"] = "6bf743306cee4c5a5d1861f944b697f3418a1a5d9b6a7cac556a429e8b7500cb"
llm = OpenAI(model_name='text-davinci-003', temperature=0.7, n= 5, best_of=5)
agent_names = ['zero-shot-react-description', 'react-docstore', 'self-ask-with-search', 'conversational-react-description', 'chat-zero-shot-react-description', 'chat-conversational-react-description']
tool_names = ["serpapi"]
tools = load_tools(tool_names)
agent = initialize_agent(tools, llm, agent=agent_names[2], verbose=True)

agent.run("Give me a large amount of information on the news from Ukraine? in high detail.")