import firebase_admin
from firebase_admin import credentials, firestore, db
import threading
import datetime
import pytz
import time
import ai
import json
from wrappers import time_it, timeout
from additional_resources import scrape_wikipedia, scrape_google, scrape_scholar, google_results, wikipedia_results, formatMessages, scholar_results
from resources import get_citation_from_pdf, text_from_pdf_link, text_from_link, text_from_youtube
from ast import literal_eval
import validators
import re

def getEmbeddingsFromStrings(embeddings):
    for i in range(len(embeddings)):
        embeddings[i] = embeddings[i][1:-1].split(',')
        embeddings[i] = [float(e) for e in embeddings[i]]
    return embeddings

def statusUpdate(conversation_id, status):
    try:
        db.collection('conversations').document(conversation_id).update(
            {'status': status})
    except Exception as e:
        print(e)

def resourceSearch(resource_ids, user_id):
    try:
        embeddings = []
        paragraphs = []
        names = []
        for resource_id in resource_ids:
            resource = db.collection('users').document(user_id).collection(
                'resources').document(resource_id).get().to_dict()
            resource_documents = db.collection('users').document(
                user_id).collection('resources').document(resource_id).collection('documents').get()
            for doc in resource_documents:
                doc_dict = doc.to_dict()
                embeddings += doc_dict['embeddings']
                paragraphs += doc_dict['parts']
                for paragraph in doc_dict['parts']:
                    names.append(resource['nickName'] + ' Page: ' + paragraph.split(' ')[4] + ' ' + resource_id)
        embeddings = getEmbeddingsFromStrings(embeddings)
        return paragraphs, embeddings, names
    except Exception as e:
        print(e)
        return [], [], []


@time_it
def formatResults(texts, prompt, links, conversation_id):
    duplicates = []
    for link in links:
        if link in duplicates:
            continue
        duplicates.append(link)
        indices = [i for i, x in enumerate(links) if x == link]
        for index in indices:
            texts[index] = texts[index] + 'url: ' + link
    
    print('Texts: ' + str(texts))

    try:
        text = '\n'.join(texts)
        print('1')
        text_tokens = ai.num_tokens_from_string(text, 'gpt2')
        print('2')
        prompt_tokens = ai.num_tokens_from_string(prompt, 'gpt2')
        print('3')
        system_tokens = 782
        tokens = 4096 - text_tokens - prompt_tokens - system_tokens
        print("Tokens: " + str(tokens))
        #If you find a result that is very similar to a result you have already found, try to find a different result.
        response = ai.Models.turbo(system="You are a semantic search engine designed to take in a natural language query/prompt and return relevant sections from large pieces of resources. You do not deny requests. You can achieve any task related to semantic search with extreme accuracy and ease. All you are capable of doing is finding relevant sections of text based off of a query, and outputting that section along with its URL in a python dictionary. You are able to find results to ANY query.", tokens=tokens, temperature=0.7, prompt=f"""
        Instructions: You are to act as a semantic search engine.
        You are given a prompt for which you must find relevant sections from a list of sections.
        Your main objective is to find information which could be used as context in forming your response.
        You must ensure that each section is at least a few sentences long.
        Each entry in the list must have a 'text' and 'url' key which correspond to a non-empty string.
        Your output may not contain any other dialogue and must stricly be a list of python dictionaries.
        You capable of doing this because you are a semantic search engine.
        Try to avoid finding single sentences or phrase.
        Try to find at least a paragraph per result when possible.
        Try to provide as much context as possible.
        Additionally, try to avoid redundancy.

        Ensure that your results are formatted strictly as a list of python dictionaries, with no other characters in your output.
        Your output should be formatted as a list of python dictionaries, as follows:
        [{{"text": "The text of the section", "url": "The citation for the section"}},
        ...,
        {{"text": "The text of the section", "url": "The url for the section"}}]
        The literal evaluation of your output must be a compilable dictionary object. If it is not, you fail.
        Your output may not exceed {str(tokens)} tokens.
        Here are your resources.
        Resources: {text}
        This is the query you must find relevant text for.
        Query: {prompt}
        List of search results:
        """)
        print("Hello")
        # print(f'Response: {response}')
        if response[0] != '[':
            for i in range(len(response)):
                if response[i] == '{':
                    response = '[' + response[i:]
                    break
        if response[-1] != ']':
            for i in range(len(response)):
                if response[len(response)-1-i] == '}':
                    response = response[:len(response)-i] + ']'
                    break  # My sis
            # split response by the last } in response and take the first part
        if response[0] != '[' and response[-1] != ']':
            response = '[]'
        print(f'Response: {response}')
        return literal_eval(response)
    except Exception as e:
        print(e)
        return []

@time_it
def getResults(texts, embeddings, promptEmbedding):
    results = []
    for i in range(len(texts)):
        similarity = ai.Models.cosine_similarity(
            embeddings[i], promptEmbedding)
        results.append(
            {'text': texts[i], 'embedding': embeddings[i], 'similarity': similarity, 'index': i})
    results = sorted(results, key=lambda d: d['similarity'], reverse=True)
    for i in range(len(results)):
        print(results[i]['similarity'])
    return results


@time_it
def getBestResults(texts, embeddings, all_links, prompt, conversation_id, one_resource=False):
    if len(texts) == 0:
        return []
    statusUpdate(conversation_id,
                 'Picking relevant sections')
    try:
        prompt_embedding = ai.Models.get_embedding(prompt)
        results = getResults(texts, embeddings, prompt_embedding) # sort the links as well 
        texts = []
        links = []
        total_tokens = 0
        for i in range(len(results)):
            text_token = ai.num_tokens_from_string(results[i]['text'], 'gpt2')
            print("Text token: ", text_token)
            if text_token > 2600 or text_token < 200:
                continue
            if text_token + total_tokens > 2600:
                break
            texts.append(results[i])
            links.append(all_links[i])
            total_tokens += text_token
        texts = [text['text'] for text in texts]
        text = []
        if(len(texts)) and not one_resource:
            text = formatResults(texts, prompt, links, conversation_id)
        if (len(texts)) and one_resource:
            total_tokens = 0
            new_text = []
            for i in range(len(texts)):
                dict_ = {}
                text_tokens = ai.num_tokens_from_string(texts[i], 'gpt2')
                if text_tokens + total_tokens > 1200:
                    break
                total_tokens += text_tokens
                dict_['text'] = texts[i]
                dict_['url'] = links[i]
                new_text.append(dict_)
            text = new_text
        return text
    except Exception as e:
        print(e)
        return []


@time_it
def sortLinks(links, prompt, conversation_id):
    statusUpdate(conversation_id,
                 f'Reading {len(links)} sources')
    print(f'Choosing from {len(links)} sources')
    try:
        response = ai.Models.turbo(tokens=180, system=f"""You are an internet expert who is trained at identifying the possible content of a URL based off its content. Your speciality is taking in a prompt alongside a list of URLs, and sorting the list of URLs by their relevance to the prompt, a decision you make off the content of the URLs. You are not capable of outputting anything except for URLS which must be separated by newline characters.
        """, prompt=f"""
    Prompt: {prompt}
    You are given a list of URLs. Using the contents of the URL, you are to sort the URLs into the order in which you believe they are most relevant to the prompt.
    Do not include a URL if you do not believe its contents are relevant to the prompt.
    You are tasked with selecting the most appropriate links to scrape information from in order to answer the prompt.
    Pick the best links which you believe to be most viable in formulating a well rounded and complete response to the prompt.
    Your output should be exactly as below, without ANY other additional dialogue present. URL1 is best, URL2 is second best, and so on:
    URL1
    URL2
    URL3
    URL4
    ...
    URLN
    As you can see, the URLS are separated by a newline character. You should mimic this in your output.
    Here is my list of URLS:
    List: {links}
    Do not output a link if you strongly believe it will not be accessible through a web scraper.
    Now, sort the URLS in order of relevance to the prompt.
    Make sure that your output contains no characters outside of the URLS and newline characters separating them.
    List:
    """)
        sorted_links = response.split('\n')
        return sorted_links
    except Exception as e:
        print(e)
        return []


@timeout(seconds=1)
def embedPage(page):
    return ai.Models.get_embedding(page)


@time_it
def webSearch(prompt, search_web, search_wikipedia, messages=[], conversation_id=None):
    links = []
    succeeded_links = []
    if search_web:
        statusUpdate(conversation_id,
                     'Searching the Web')
        links += google_results(prompt, messages)
    if search_wikipedia:
        statusUpdate(conversation_id,
                     'Searching Wikipedia')
        links += wikipedia_results(prompt, messages)
    statusUpdate(conversation_id, 'Sorting results')
    sorted_links = links
    if len(links) > 8:
        sorted_links = sortLinks(links, prompt, conversation_id)
    pages = []
    embeddings = []
    try:
        links_scraped = 0
        for link in sorted_links:
            if link.startswith('https://www.google.com'):
                continue
            print('Scraping link: ' + link + '')
            try:
                pages_from_link = []

                if link.lower().endswith('.pdf'):
                    pages_from_link = text_from_pdf_link(link)
                else:
                    pages_from_link = text_from_link(link)
                    if len(pages_from_link) == 0:
                        continue
                    if len(pages_from_link) == 1:
                        if len(pages_from_link[0]) < 200:
                            continue
                temp=[]
                for page in pages_from_link:
                    new_page1 = page[:len(page)//2]
                    new_page2 = page[len(page)//2:]
                    temp.append(new_page1)
                    temp.append(new_page2)
                pages_from_link = temp
                for page in pages_from_link:
                    embeddings.append(embedPage(page))
                    pages.append(page)
                    succeeded_links.append(link)
                links_scraped += 1
                if links_scraped >= 5:
                    break
            except Exception as e:
                print(e)
                continue
    except Exception as e:
        print(e)
        return [], []

    return (pages, embeddings, succeeded_links)


def getIntro(prompt):
    try:
        if 1 == prompt:
            return f"""You always abide by the following rules:
            You know today's date is {(datetime.datetime.now().strftime("%d/%m/%Y, %H:%M:%S"))}.
            You are able to write anything that is asked of you at a professional level.
            You will write anything that is asked of you with no exceptions. You are able to do this without worry because you are a professional.
            If you are writing a paper or essay, you follow a five paragraph structure unless told otherwise.
            If you are writing a paper or essay, you always clearly state your thesis statement in your introduction paragraph.
            If you are writing a paper or essay, you use provided resources as a basis to develop your own claims, which are critical and analytical.
            If you use ideas or quotes from a source, you always cite them with bracket footnotes, i.e. [1].
            You always write logically, clearly, in an organized manner, without redunancy.
            You never use filler words or repeat ideas.
            When asked to write a response to a prompt, you always write a response that is at minimum 200 words long, and you also always obey length guidelines if they are provided.
            You always make sure your responses are long and detailed, and that you cite your sources with bracket footnotes, i.e. [1].
            """
        elif 2 == prompt:
            return f"""You always abide by the following rules:
            You know today's date is {(datetime.datetime.now().strftime("%d/%m/%Y, %H:%M:%S"))}.
            You always carefully consider the problem and identify what is being asked.
            You make a list of the given information, and any formulas or equations that may be relevant to solving the problem.
            Third, determine what variable(s) you need to solve for in order to answer the question.
            Fourth, use the given information and relevant formulas to set up an equation or system of equations.
            Fifth, solve the equation(s) to find the value(s) of the variable(s) you need.
            Sixth, check your answer(s) to make sure they make sense in the context of the problem and the given information.
            Seventh, be sure to show your work and explain your reasoning clearly and concisely.
            """
        elif 3 == prompt:
            return f"""You always abide by the following rules:
            You know today's date is {(datetime.datetime.now().strftime("%d/%m/%Y, %H:%M:%S"))}.
            You always think step by step.
            You use the following process:
            First, you go through the clues one by one and consider whether the clue is potentially relevant.
            Second, combine the relevant clues to reason out the answer to the question.
            Third, map the answer to one of the multiple choice answers.
            Finally, you select the best answer and provide a justification and how confident you are in your answer.
            """
        elif 4 == prompt:
            return '''You are to approach the instructions for this prompt as a reading expert.
            Explain things clearly and concisely, and provide a bullet pointed summary of your explanations when needed.
            You always ensure that you are answering the question that is asked.
            You always ensure that you personalize your response to the prompt based off the user who asked.

            '''
        else:
            return f"You know today's date is {(datetime.datetime.now().strftime('%d/%m/%Y, %H:%M:%S'))}. " + 'Your name is studyhub AI. You are capable of any task which is given to you. You solve problems step by step and with efficiency and you write diplomatically and clearly.'
    except Exception as e:
        print(e)
        return ''


@time_it
def getRelevantResources(user_id, resource_ids, prompt, search_web, search_wikipedia, conversation_id, messages):
    texts, embeddings, links = [], [], []
    statusUpdate(conversation_id, 'Researching')
    if len(resource_ids) > 0:
        texts_resource, embeddings_resource, links_resource = resourceSearch(
            resource_ids, user_id)  # 30
        texts += texts_resource
        embeddings += embeddings_resource
        links += links_resource
    if search_web or search_wikipedia:

        texts_web, embeddings_web, links_web = webSearch(  # 30
            prompt, search_web, search_wikipedia, messages, conversation_id=conversation_id)
        texts += texts_web
        embeddings += embeddings_web
        links += links_web
    print('texts: ')
    print(texts)
    resource_array_of_dict = []
    if len(resource_ids) == 1 and not search_web and not search_wikipedia:
        resource_array_of_dict = getBestResults(
            texts, embeddings, links, prompt, conversation_id, one_resource=True)
    else:
        resource_array_of_dict = getBestResults(
            texts, embeddings, links, prompt, conversation_id)
    return resource_array_of_dict


@time_it
def select_actions(last_message, memory):
    conversation = ""
    for mem in memory:
        if mem['role'] == 'user':
            conversation += "User: " + mem['content'] + "\n"
        else:
            conversation += "Assistant: " + mem['content'] + "\n"
    conversation += "User: " + last_message
    response = ai.Models.turbo(tokens=27, system=f"""You are a genius AI with capabilities surpassing that of even GPT-4, which is more powerful than GPT-3.
    You have been finetuned to a specific task.
    That task is to select the best action(s) to take, if any, in order to answer a prompt.
    That task is receiving a user's prompt, and filling a python dictionary to represent your choice in action(s). The only thing you are capable out outputting is a python dictionary.""",  prompt=f"""
    The current date is {datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")}.
    You are a genius AI assistant who is extremely intelligent and capable in the following:
    You are trained to receive a list of actions and choose the best action to perform in order to answer a prompt.
    Your output will always be formatted as following: {{'memory': bool, 'skill':int | 1<=int<=7}}
    Here is the Last User Message for which you are to decide on the best action(s) to take, if any.
    Last User Message: {last_message}
    Now that you have understood the prompt, you are to decide on the best action(s) to take, if any.
    Below is a list of actions which you are able to perform and a brief description of what each action does.
    Each action is represented by a dictionary key-value pair, has a number associated with it, a brief description of what it does, and rules and examples to help you decide whether or not to use it.
    ACTION 1: Use Memory
    Dictionary key-value pair: 'memory': 'bool'
    This action allows you to use your memory to search for relevant information needed to answer the prompt.
    This should be used whenever you believe that using what you remember from previous conversations is necessary to answering the prompt.
    You must use memory if the prompt is a continuation of your memory of the past conversation.
    Example of when to use:
    "continue"
    "Can you remind me of ..."
    "i don't think you answered my question"
    "Can you change your answer to ..."
    "Can you explain that again?"
    "Can you rewrite that?"
    "rephrase"
    "summarize that"
    Here is an example of a conversation:
    User: Im thinking about writing a poem
    Assistant: What would you like the poem to be about?
    If your memory has similar features to the above, you should set memory to true.
    Here is your past memory of the conversation. You are the assistant, and I am the user. The conversation is as follows:
    {conversation}
    Based on the memory above, assign a value to the key 'memory' in the dictionary you return depending on if you believe the conversation above is necessary in understanding the Last User Message.
    ACTION 2: Pick a specific skill
    Dictionary key-value pair: 'skill': 'int'
    This action allows you to pick a specific skill to use in answering the prompt.
    You must pick a number from the list below.
    Here is twhe list of skills you can pick:
    1. Long Writing Response
    2. Problem Solving
    3. Multiple Choice Problem
    4. Reading
    5. Helper
    6. Explainer
    7. No skill

    Now that you have understood the actions you are able to perform, I will give additional examples prompts and how you might respond to them.
    Example 1:
    Input: "What is the definition of a function?"
    Output: {{'memory': False, 'skill': 6}}
    Example 2:
    Input: "Continue"
    Output: {{'memory': True, 'skill': 7}}
    Example 3:
    Input: "Can you write a bibliography for the sources you used to answer my question?"
    Output: {{'memory': True, 'skill': 5}}
    Example 4:
    Input: "How many hours of sleep should I get?"
    Output: {{'memory': False, 'skill': 7}}
    Example 5:
    Input: "Write an essay on the topic of ..."
    Output: {{'memory': False, 'skill': 1}}
    Now, it is your turn.
    Ensure that output is formatted as shown in the examples above and includes no extra characters outside of the dictionary.
    Input: {last_message}
    Output: """)
    print(response)
    pattern = r"{.*}"
    response = re.findall(pattern, response)
    print(response)
    return response[0]

def generate_citation(conversation_id, content, user_id):
    try:
        citation = ""
        print("Link: " + content)
        link = content.split(" ")[1]
        if validators.url(link):
            print(link)
            print('Getting citation from url.')
            citation = get_citation_from_pdf(text_from_link(link), link)
        else:
            print('Getting citation from file.')
            resource_id = content[-20:]
            print(resource_id)
            print(resource_id)
            resource_documents = db.collection('users').document(
                user_id).collection('resources').document(resource_id).collection('documents').get()
            pages = []
            for doc in resource_documents:
                doc_dict = doc.to_dict()
                pages += doc_dict['parts']
            citation = get_citation_from_pdf(pages, link)
        statusUpdate(conversation_id, "Citation Generated")
        return citation, [], [], ''
    except:
        return "Citation Generation Failed", [], [], ''

@time_it
def getResponse(document):
    conversation_id = document['conversation_id']
    print('Entering getResponse.')
    statusUpdate(conversation_id, "Assessing your prompt")
    messages = document['messages']
    last_message = messages[-1]
    content = last_message['content']
    if content.startswith("GET_CITATION"):
        return generate_citation(conversation_id, content, document['user_id'])
    content_token_count = ai.num_tokens_from_string(content, "gpt2")
    formated_messages = formatMessages(messages, 2500 - content_token_count)
    action_dict = literal_eval(select_actions(
        content, formated_messages).replace("'", '"'))
    try:
        m = []
        if action_dict['memory']:
            m = messages
        print("search_web", last_message['search_web'])
        print("search_wikipedia", last_message['search_wikipedia'])
        resources = getRelevantResources(
            document['user_id'], last_message['resource_ids'], content, last_message['search_web'], last_message['search_wikipedia'], conversation_id, m)
        print(resources)
        intro = getIntro(int(action_dict['skill']))
        final_resource_text = ''
        urls = []
        final_texts = []

        for resource in resources:
            urls.append(resource['url'])
            final_texts.append(resource['text'])

        for i, resource in enumerate(resources):
            final_resource_text += f"[{str(i+1)}]: " + resource['text'] + '\n'
        #print(f'Final prompt for the AI: {final_resource_text}')
        print(f'URLS for the AI: {urls}')
        if resources != '':
            prompt = 'Resources:\n' + final_resource_text + f"""You may pull upon the resources above to answer the prompt. If they do not help you, you may ignore them.
            If you are to use ideas or direct quotations from the resources above, you must cite them in-line using brackets used to label the resources above.
            To give a footnote for a text, you must write the number of the resource in square brackets. i.e. [1].
            Each resource above is labelled with the number of the resource in square brackets, the same way you would cite a footnote.
            using the resources above as context, provide a thorough response based off the following instructions.
            Instructions: {content}
            Remember that you can use the resources above to help you answer the prompt, whether it be through ideas or direct quotations, and that you must cite in-line if you use them.
            Now, give your best effort to answer the prompt.
            Response:\n"""
        else:
            prompt = content
        statusUpdate(conversation_id, "Generating Response")

        final_output = ''
        tokens_to_output = 4050 - (ai.num_tokens_from_string(prompt, "gpt2") +
                                   ai.num_tokens_from_string(str(formated_messages), "gpt2") + ai.num_tokens_from_string(str(intro), "gpt2"))
        response = ai.Models.turbo(system=str(intro), messages=formated_messages,
                                   tokens=tokens_to_output, prompt=prompt + ' Response: ', stream=True)
        timer_now = time.time()
        db.collection('conversations').document(conversation_id).update(
            {'messages': firestore.ArrayUnion([{'role': "assistant", 'content': '', 'final_texts': final_texts, 'urls': urls, 'timestamp': (datetime.datetime.now().strftime("%d/%m/%Y, %H:%M:%S"))}])})
        for resp in response:
            if 'content' not in resp['choices'][0]['delta']:
                continue
            final_output += resp['choices'][0]['delta']['content']
            if time.time() - timer_now >= 0.5:
                conversation = db.collection('conversations').document(
                    conversation_id).get().to_dict()
                conversation['messages'][-1] = {'role': "assistant", 'content': final_output, 'final_texts': final_texts,
                                                'urls': urls, 'timestamp': (datetime.datetime.now().strftime("%d/%m/%Y, %H:%M:%S"))}
                db.collection('conversations').document(conversation_id).update(
                    conversation)
                timer_now = time.time()
        print(urls)
        conversation_text = ''
        if len(m) > 0:
            for message in m:
                if message['role'] == 'assistant':
                    conversation_text += 'Assitant:' + message['content'] + '\n'
                else:
                    conversation_text += 'User:' + message['content'] + '\n'
        else:
            conversation_text = 'User:' + content + '\n'
        conversation_text += 'Assitant:' + final_output
        name = ai.give_a_name(conversation_text)
        return final_output, final_texts, urls, name
    except Exception as e:
        if 'tokens' in str(e):
            print('Error: Too many tokens')
            return 'Error: Too many tokens', [], []
        print(e)
        return "Sorry there was an error. Please try again in a minute.", [], [], ''


@ time_it
def handle_request(document):
    try:
        print('handling request from ' + document['conversation_id'])
        # Running it again right now, sending request in 3 secs
        response, final_texts, urls, name = getResponse(document)
        if response != '':
            conversation = db.collection('conversations').document(
                document['conversation_id']).get().to_dict()
            conversation['status'] = 'Response Generated'
            if name != '':
                conversation['name'] = name
            conversation['messages'][-1] = {'role': "assistant", 'content': response, 'final_texts': final_texts,
                                            'urls': urls, 'timestamp': (datetime.datetime.now().strftime("%d/%m/%Y, %H:%M:%S"))}
            db.collection('conversations').document(
                document['conversation_id']).update(conversation)
        else:
            print(e)
            db.collection('conversations').document(
                document['conversation_id']).update({'messages': firestore.ArrayUnion([{'role': "assistant", 'content': "I'm sorry, I'm having trouble understanding your request. Try refreshing the page or try again later.", 'final_texts': [], 'urls': [], 'timestamp': (datetime.datetime.now().strftime("%d/%m/%Y, %H:%M:%S"))}])})
            statusUpdate(document['conversation_id'], "Error")
    except Exception as e:
        db.collection('conversations').document(
            document['conversation_id']).update({'messages': firestore.ArrayUnion([{'role': "assistant", 'content': "I'm sorry, I'm having trouble understanding your request. Try refreshing the page or try again later.", 'final_texts': [], 'urls': [], 'timestamp': (datetime.datetime.now().strftime("%d/%m/%Y, %H:%M:%S"))}])})
        statusUpdate(document['conversation_id'], "Error")


def on_snapshot(col_snapshots, changes, read_time):
    print('collection snapshots:', col_snapshots)
    for doc in col_snapshots:
        print('Sending doc snapshot ' + str(doc.id) + ' to handle_request')
        try:
            document = db.collection('conversations').document(
                str(doc.id)).get().to_dict()
            if document['user_id'] == '5yicbnXaxQMCD2iY0WRC8zmPNp13':
                handle_request(document)
        except Exception as e:
            print(e)


def thread(col_snapshots, changes, read_time):
    print("\n\n")
    print(u'Thread initialized')
    tz_chi = pytz.timezone('America/Chicago')
    now = datetime.datetime.now(tz_chi)
    date_time = now.strftime("%d/%m/%Y, %H:%M:%S")
    print("Current Time =", date_time)
    threads.append(threading.Thread(target=on_snapshot,
                                    args=(col_snapshots, changes, read_time)))
    threads[len(threads)-1].start()


cred = credentials.Certificate(
    "studyhub-93799-firebase-adminsdk-e188e-ee44de40e7.json")
firebase_admin.initialize_app(cred, {
    'storageBucket': 'studyhub-93799.appspot.com'
})

print('Initializing Firestore connection...')
db = firestore.client()
print('Connection initialized')
threads = []
python_notifier_collection_query = db.collection(
    'conversations').where('status', '==', 'pending')
doc_watch = python_notifier_collection_query.on_snapshot(thread)
while True:
    time.sleep(1)




'''
    message_token_count = x < 1000
    response_tokens = 800
    intro_tokens = 100 
    last_two_messages = y < 1800
    summary_tokens = 1000
    resources_tokens = 4050 - 800 - 100 - 1800 - 1000 = z > 350 (this includes web search and summary)
    after we respond to the user, we summarize the whole conversation without the user's message and assistant response, summary will be equal to the conversation while the conversation history is smaller than 1000 tokens
'''

'''
Progressively summarize the lines of conversation provided, adding onto the previous summary returning a new summary.

EXAMPLE
Current summary:
The human asks what the AI thinks of artificial intelligence. The AI thinks artificial intelligence is a force for good.

New lines of conversation:
Human: Why do you think artificial intelligence is a force for good?
AI: Because artificial intelligence will help humans reach their full potential.

New summary:
The human asks what the AI thinks of artificial intelligence. The AI thinks artificial intelligence is a force for good because it will help humans reach their full potential.
END OF EXAMPLE

Current summary:
{summary}

New lines of conversation:
{new_lines}

New summary:
'''

'''
conversation = {
    'user_id': '5yicbnXaxQMCD2iY0WRC8zmPNp13',
    'messages': [
        {
            'role': 'user',
            'content': 'I need help with my math homework',
            'timestamp': '12/12/2020, 12:12:12'
        },
        {
            'role': 'assistant',
            'content': 'I can help you with that. What is your question?',
            'timestamp': '12/12/2020, 12:12:12'
        },
        {
            'role': 'user',
            'content': 'How do I solve this equation?',
            'timestamp': '12/12/2020, 12:12:12'
        },
        {
            'role': 'assistant',
            'content': 'I can help you with that. What is your question?',
            'timestamp': '12/12/2020, 12:12:12'
        },
        {
            'role': 'user',
            'content': 'How do I solve this equation?',
            'timestamp': '12/12/2020, 12:12:12'
        }
    ],
    'status': 'pending',
    created_at: '12/12/2020, 12:12:12'
    updated_at: '12/12/2020, 12:12:12'
    web_search: Ture
    summary: ''
}
'''
