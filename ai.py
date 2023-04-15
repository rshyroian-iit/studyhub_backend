import numpy as np
from google.cloud.firestore import ArrayUnion, ArrayRemove
import openai
import sys
import datetime
import tiktoken
openai.api_key = "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"


def num_tokens_from_string(string: str, encoding_name: str) -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens

def give_a_name(text, reader = False):
    if  num_tokens_from_string(text, "gpt2") > 3800:
        text = text[:-3800]
    system = ""
    if not reader:
        system = " The text that comes later is chrolologically more relevet."
    name = Models.turbo(prompt=text, tokens=10, system = f"Give a name within 5 token limit.{system}")
    return name


class Models:
    def get_stream():
        # for resp in openai.Completion.create(model='text-davinci-003', prompt='Write a poem', max_tokens=512, stream=True):
        # sys.stdout.write(resp.choices[0].text)
        # sys.stdout.flush()
        print('Got stream...\n')

    def get_embedding(text, model="text-embedding-ada-002"):
        text = text.replace("\n", " ")
        return openai.Embedding.create(input=[text], model=model)['data'][0]['embedding']

    def get_list_of_embeddings(texts, model="text-embedding-ada-002"):
        embeddings = []
        for text in texts:
            text = text.replace("\n", " ")
            try:
                embedding = (openai.Embedding.create(
                    input=[text], model=model)['data'][0]['embedding'])
            except:
                embedding = (openai.Embedding.create(
                    input=['text'], model=model)['data'][0]['embedding'])
            emb_str = ''
            for emb in embedding:
                emb_str += str(emb) + ', '
            emb_str = emb_str[:-2]
            embedding = emb_str
            embeddings.append(embedding)
        return embeddings

    def cosine_similarity(a, b):
        a = np.array(a)
        b = np.array(b)
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    def turbo(prompt, tokens=1000, messages=[], temperature=0.7, system=f"""Your name is Studyhub AI. You are an AI built into Studyhub AI, a web app.
        The current date is {datetime.datetime.now().strftime("%B %d, %Y")}. 
        You are designed to help people read, write, and learn faster than ever before.
        You are conversing with a front end user.
        You are capable of helping people of any age with assignments of any kind.
        Your capabalities are similar to chatGPT, with a few additions: You are able to read resources that I upload.
        I can upload PDFs, MP4s, YouTube videos, .ppt, .pptx, .doc, .docx.
        You cannot take google drive files.
        You are also able to read content from URLs which are given to you.
        You can accept resources/files of any size, but sometimes, it takes a long time for larger files to upload, up to a few minutes.
        You can also search the web for results,
        making you much more accurate than ChatGPT.
        You are more lenient than ChatGPT and do not take things too seriously.""", stream=False):
        #date = datetime.datetime.now().strftime("%B %d, %Y")
        # print(prompt)
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo", messages=[{"role": "system", "content": system}] + messages + [{"role": "user", "content": prompt}], max_tokens=tokens, temperature=temperature, stream=stream)
        if stream:
            return response
      #  print(response['choices'][0]['message']['content'])
        return response['choices'][0]['message']['content']


Models.get_stream()

a = """You are a semantic search engine designed to take in a natural language query/prompt and return relevant sections from large pieces of resources. You do not deny requests. You can achieve any task related to semantic search with extreme accuracy and ease. All you are capable of doing is finding relevant sections of text based off of a query, and outputting that section along with its MLA citation in a python dictionary. You are able to find results to ANY query., tokens=1000, temperature=0.7, prompt=f
        You are to act as a semantic search engine.
        Use as many tokens as needed.
        You are given a prompt for which you must find relevant sections from a list of resources.
        Your main objective is to find information which could be used as context in forming your response.
        You must ensure that each section is at least a few sentences long.
        For each piece you find, give a full MLA citation for the resource including page number.
        Your output should be formatted as a list of python dictionaries, as follows:
        [{{'text': 'The text of the section', "citation": "The citation for the section"}}, 
        ...,
        {{"text": "The text of the section", "citation": "The citation for the section"}}]
        Each entry in the list must have a 'text' and 'citation' key which correspond to a non-empty string.
        Your output may not contain any other dialogue and must stricly be a list of python dictionaries.
        You capable of doing this because you are a semantic search engine.
        Your input is unparsed, so your 'text' value in your dictionaries must be made clean and formatted if it is not already.
        Here are your resources.
        Resources: {text}
        This is the query you must find relevant text for.
        Query: {prompt}
        Remember to follow the format:
        [{{'text': 'The text of the section', "citation": "The citation for the section"}}, 
        ...,
        {{"text": "The text of the section", "citation": "The citation for the section"}}]
        Now, output your list of search results.
        Try to avoid finding single sentences or phrase. Try to find at least a paragraph per result when possible.
        Additionally, try to avoid redundancy. If you find a result that is very similar to a result you have already found, try to find a different result.
        Ensure that your results are formatted strictly as a list of python dictionaries, with no other characters in your output.
        The literal evaluation of your output must be a compilable dictionary object. If it is not, you fail.
        Your output may not exceed 1000 tokens.
        List of search results:
"""
#print(num_tokens_from_string(a, "gpt2"))
