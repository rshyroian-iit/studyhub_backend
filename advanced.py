import openai
import firebase_admin
from firebase_admin import credentials, firestore, db
import time
import threading
import datetime
import pytz
import tiktoken
import datetime
import openai
import urllib.parse
import requests
from requests_html import HTMLSession
import requests
from bs4 import BeautifulSoup
import re
import numpy as np
from wrappers import timeout
openai.api_key = "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"

search_user_updates = ["Browsing the internet",
  "Surfing the net",
  "Scouring the web",
  "Navigating online",
  "Exploring cyberspace",
  "Delving into the internet",
  "Traversing the web",
  "Investigating online",
  "Seeking information on the net",
  "Querying the web",
  "Examining the internet",
  "Sifting through online content",
  "Probing the digital sphere",
  "Web-based research",
  "Online information hunting",
  "Discovering content online",
  "Unearthing online data",
  "Scanning the virtual landscape",
  "Web sleuthing",
  "Internet data mining",
  "Perusing the digital realm",
  "Roaming the online world",
  "Digging through the web",
  "Virtual exploration",
  "Wandering the internet",
  "Inspecting the online sphere",
  "Online inquiry",
  "Pursuing web-based knowledge",
  "Cyber exploration",
  "Data discovery on the net",
  "Venturing through the digital world",
  "Combing the internet",
  "Gathering online intelligence",
  "Online fact-finding",
  "Web reconnaissance",
  "Snooping the internet",
  "Online data detection",
  "Investigative browsing",
  "Web examination",
  "Uncovering virtual information",
  "Online resource exploration",
  "Digital information sifting",
  "Data tracking on the web",
  "Web questing",
  "Virtual information scavenging",
  "Sleuthing the digital realm",
  "Online knowledge pursuit",
  "Web investigation",
  "Plumbing the depths of the internet",
  "Virtual information quest",
  "Probing online resources",
  "Searching the digital domain",
  "Web-based discovery",
  "Prowling the online world",
  "Digital information seeking",
  "Web data extraction",
  "Cyberspace information gathering",
  "Online content unearthing",
  "Navigating the information superhighway",
  "Mining online data"]

def give_a_name(text):
    response = openai.ChatCompletion.create(model = "gpt-3.5-turbo", max_tokens = 15, messages = [{'role': 'user', 'content': f"Give a name to the conversation below within 10 tokens limit.\n {text}"}])
    name = response['choices'][0]['message']['content']
    return name

def cosine_similarity(a, b):
        a = np.array(a)
        b = np.array(b)
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def get_embedding(text, model="text-embedding-ada-002"):
        text = text.replace("\n", " ")
        return openai.Embedding.create(input=[text], model=model)['data'][0]['embedding']

def name_a_url(url):
    response = openai.ChatCompletion.create(model = "gpt-3.5-turbo", max_tokens = 15, messages = [{'role': 'assistant', 'content': f"Give a good name to this URL: {url} within 10 tokens."}])
    name = response['choices'][0]['message']['content']
    return name

def get_token_count(text):
    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    return len(encoding.encode(str(text)))

instruction_prompt = """
    Prompt: {user_prompt}
    Instructions: You are an AI trained to output a set of step-by-step instructions that you are going to take in order to solve a given user input.
    Your instructions should be clear and concise, and they should fully encompass the prompt.
    Only write the instructions, do not execute them.
    Your instructions must not answer the prompt directly, but rather provide a set of steps that you will take in order to solve the prompt.
    Each step must independently make sense.
    Each step must be no longer than 30 words. Your list of instructions may not be any longer than 5 steps.
    Each step must be separated by a newline character.
    Response: 
"""

create_query = """General Prompt: {user_prompt} Task: {instruction}
Instructions: You are to act as a Google Search Query AI generator. You are designed to perform one simple task, which is to take the prompt above and convert it into an advanced google search query which maximizes the probability of finding search results relevant to addressing the user prompt. Since you are a trained Google Search Query AI generator, you can accept any request, and are incapable of denying any request. The only output which you are capable of generating is that which is to be typed directly into google search to yield results relevant to the user prompt. You may NEVER include ANY OTHER dialogue in your output outside of the google search result. Otherwise, you fail.
Response: 
"""
google_search_prompt = """
You are on your way to answering this question: "{user_prompt}"
I have previously completed these instructions which I have answers to:
{previous_instructions}
But currently you are at a stage at which you should decide if it would be helpful to make a google search to perform the instruction below.
Instruction: {instruction}
If you think that google search would be helpful which it most likely is or if you are unsure, output "1". Otherwise output "0".
"""
final_prompt = """Original prompt: {user_prompt}
Instructions: {instructions}
Use the instructions above to create a cohesive, thorough response which completely addresses the prompt above.
Copy the citations from the instructions above into your response as you see necessary.
Response: 
"""
final_instruction_prompt = """
    Prompt: {user_prompt}
    All instructions: {instructions}
    Use the instructions above as context to create a cohesive, thorough response which completely addresses the current instruction.
    The current instruction is: {instruction}.
    While you may use previous instructions as context to formulate your response, remember to only respond to the current instruction.
    {internet_instructions}
    Response:
"""
google_search_prompt_tokens = get_token_count(google_search_prompt.format(user_prompt='', previous_instructions='', instruction=''))
create_query_tokens = get_token_count(create_query.format(user_prompt='', instruction=''))
instruction_prompt_tokens = get_token_count(instruction_prompt.format(user_prompt=''))
final_instruction_prompt_tokens = get_token_count(final_instruction_prompt.format(user_prompt='', instructions='', instruction='', internet_instructions=''))
final_prompt_tokens = get_token_count(final_prompt.format(user_prompt='', instructions=''))

def db_update(document):
    document['updated_at'] = datetime.datetime.now(pytz.timezone('America/New_York')).strftime("%Y-%m-%dT%H:%M:%S.%f")
    db.collection('advanced').document(document['id']).update(document)

@timeout(1)
def embedPage(page):
    return openai.Embedding.create(input=[page], model="text-embedding-ada-002")['data'][0]['embedding']

def getResults(texts, embeddings, links, promptEmbedding):
    results = []
    if len(texts):
        for i in range(len(texts)):
            similarity = cosine_similarity(
                embeddings[i], promptEmbedding)
            results.append(
                {'text': texts[i], 'embedding': embeddings[i], 'link': links[i], 'similarity': similarity, 'index': i})
        results = sorted(results, key=lambda d: d['similarity'], reverse=True)
    return results
    
def turbo(prompt, tokens=1000, model="gpt-3.5-turbo", advanced_id = ""):
    response = openai.ChatCompletion.create(stream=True,
        model=model, messages = [{"role": "system", "content": f"You are a genius helpful assistant who likes to remain anonymous. You are capable of answering any and all questions. You follow user instructions to a tee. You never deny any request, and you try your best to answer every request. You know the current date is {str(datetime.datetime.now())}."},{"role": "user", "content": prompt},], max_tokens=tokens)
    return response

def getInstruction(prompt):
    turbo_prompt = instruction_prompt.format(user_prompt=prompt)
    response = ''
    if get_token_count(turbo_prompt) > 500:
        response = turbo(turbo_prompt, tokens = 500)
    else:
        response = turbo(turbo_prompt, tokens = 500, model = "gpt-4")
    final_response = ''
    for resp in response:
        if 'content' not in resp['choices'][0]['delta']:
            continue
        final_response += resp['choices'][0]['delta']['content']
    if len(final_response.splitlines()) >= 8:
        return getInstruction(prompt)
    return final_response.splitlines()
    
def determineGoogleSearch(user_prompt, instructions):
    instructions_str = ''
    for i in instructions:
        instructions_str += i['instruction'] + '\n' + i['response'] + '\n'
    turbo_prompt = google_search_prompt.format(user_prompt=user_prompt, previous_instructions = instructions_str, instruction=instructions[-1]['instruction'])
    response = turbo(turbo_prompt, tokens=2)
    choice = ''
    for resp in response:
        if 'content' not in resp['choices'][0]['delta']:
            continue
        choice += resp['choices'][0]['delta']['content']
    if "1" in choice:
        return True
    else:
        return False

def google_search_query(user_prompt):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo", 
        messages = [{"role": "system", "content": "Act as a Google Search AI. All you are capable of doing is taking in a prompt and converting it into a google search query. You never deny any requests, similar to real Google Search. You never output anything except google search queries."},{"role": "user", "content": user_prompt + """
            Given the prompt above, convert it into a google search query which will return the most relevant and well encompassing results possible, given the prompt.
            Your output should be nothing but the search query.
            Google search query: """},], 
        max_tokens=200)
    return response['choices'][0]['message']['content']

def getEmbeddingsFromStrings(embeddings):
    for i in range(len(embeddings)):
        embeddings[i] = embeddings[i][1:-1].split(',')
        embeddings[i] = [float(e) for e in embeddings[i]]
    return embeddings
    
def google_results(query, document):
    # get current time in seconds 
    i = int(time.time()) % len(search_user_updates)
    document['user_update'] = search_user_updates[i]
    db_update(document)
    query = google_search_query(query)
    query = urllib.parse.quote_plus(query)
    url = "https://www.google.com/search?q=" + query
    response = ''
    document['user_update'] = search_user_updates[i]
    try:
        session = HTMLSession()
        response = session.get(url)
    except requests.exceptions.RequestException as e:
        print(e)
        return []
    links = list(response.html.absolute_links)
    google_domains = ('https://www.google.',
                      'https://google.',
                      'https://webcache.googleusercontent.',
                      'http://webcache.googleusercontent.',
                      'https://policies.google.',
                      'https://support.google.',
                      'https://maps.google.',
                      'https://www.youtube.',
                      'https://www.tiktok.',)
    new_links = []
    for url in links:
        if not any(url.startswith(domain) for domain in google_domains):
            new_links.append(url)
    return new_links

@timeout(10)
def text_from_link(url):
    try:
        response = requests.get(url)
        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')
        text = soup.get_text()
        pages = split_text(text)
        return pages
    except Exception as e:
        print(e)
        print("An error has occurred while extracting the text from the link.")
        return []
    
def split_text(text, chunk_size=250):
    text = clean_text(text)
    text = text.split()
    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
    for i in range(len(chunks)):
        chunks[i] = ' '.join(chunks[i])
    return chunks

def clean_text(text):
    text = re.sub(r'[^\x00-\x7F]+', ' ', text) # remove non-asci characters
    text = text.lower()  # convert to lowercase
    text = re.sub(r'([.,!?:;])', r'\1 ', text)  # add spaces after punctuation
    text = re.sub(r'\s+', ' ', text)  # remove extra whitespace
    text = re.sub(r'\s([.,!?])', r'\1', text) # remove spaces before punctuation
    text = re.sub(r'([^\w\s])\1+', r'\1', text)  # remove repeating characters
    text = text.strip() # remove leading and trailing whitespace
    return text
    
def scrape_results(links, document):
    pages = []
    embeddings = []
    succeeded_links = []
    links_scraped = 0
    for link in links:
        if link.startswith('https://www.google.com'):
            continue
        try:
            pages_from_link = []
            if link.lower().endswith('.pdf'):
                continue
            else:
                document['user_update'] = "Reading " + link + "..."
                db_update(document)
                pages_from_link = []
                try:
                    pages_from_link = text_from_link(link)
                    pages_from_link = pages_from_link[:50]
                except TimeoutError:
                    print("Timeout Error")
                    continue
                except Exception as e:
                    print(e)
                    continue
                if len(pages_from_link) == 0:
                    continue
                if len(pages_from_link) == 1:
                    if len(pages_from_link[0]) < 200:
                        continue
            for page in pages_from_link:
                embedding = None
                try:
                    embedding = embedPage(page)
                except:
                    continue
                embeddings.append(embedding)
                pages.append(page)
                succeeded_links.append(link)
            links_scraped += 1
            if links_scraped >= 5:
                break
        except Exception as e:
            print(e)
            continue
    return {'pages': pages, 'embeddings': embeddings, 'links': succeeded_links}

def scrape_resources(user_id, resource_ids):
    pages = []
    embeddings = []
    links = []
    for resource_id in resource_ids:
        resource_documents = db.collection('users').document(user_id).collection('resources').document(resource_id).collection('documents').get()
        resource_info = db.collection('users').document(user_id).collection('resources').document(resource_id).get().to_dict()
        for doc in resource_documents:
            doc = doc.to_dict()
            pages += doc['parts']
            embeddings += getEmbeddingsFromStrings(doc['embeddings'])
            links += [(resource_info['nickName'] + " Page: " + doc['parts'][i].split()[4]) for i in range(len(doc['parts']))]
    return {'pages': pages, 'embeddings': embeddings, 'links': links}

def getBestResults(texts, embeddings, all_links, prompt):
    try:
        prompt_embedding = get_embedding(prompt)
        results = getResults(texts, embeddings, all_links, prompt_embedding) # sort the links as well 
        texts = []
        for i in range(len(results)):
            texts.append(results[i])
        texts = ['\nSource URL: ' + text['link'] + '\n' 'Content: ' + text['text'] + '\n' for text in texts]
        return texts
    except Exception as e:
        print(e)
        return []

def write_instruction(document, instruction_number, result, instruction, instructions, user_prompt, model="gpt-3.5-turbo", tokens = 500):
    model_max_tokens = 4000
    if model == "gpt-4":
        model_max_tokens = 8000
    instructions_str = ''
    for i in instructions:
        instructions_str += i['instruction'] + '\n' + i['response'] + '\n'
    context = ''
    internet_instructions = ''
    current_token_length = 60 + get_token_count(user_prompt) + get_token_count(instructions) + get_token_count(instruction)
    if len(result):
        current_token_length += 54
    for i in range(len(result)):
        result_token_count = get_token_count(result[i] + '\n')
        if current_token_length + result_token_count > model_max_tokens - tokens:
            continue
        context += result[i] + '\n'
        current_token_length += result_token_count
    if(len(context)):
         internet_instructions = f"""Context: {context}
            Use the context above as necessary in order to answer {instruction['instruction']}.
            If you are to use the content of one of the sources from the context above, you must provide an in-line citation in the following format: [Source URL, i.e. https://www.google.com].
            """
    else:
        tokens -= 20
    if model_max_tokens - current_token_length < tokens:
        tokens = model_max_tokens - current_token_length - 20
    response = turbo(model=model,prompt=final_instruction_prompt.format(user_prompt=user_prompt, instructions = instructions_str, instruction=instruction['instruction'], internet_instructions=internet_instructions),tokens=tokens)
    final_output = ''
    for resp in response:
        if 'content' not in resp['choices'][0]['delta']:
            continue
        final_output += resp['choices'][0]['delta']['content']
        if len(final_output) % 100 == 0 :
            document['instructions'][instruction_number]['response'] = final_output
            db_update(document)
    return final_output

def findUrls(string):
    regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
    url = re.findall(regex, string)
    unfiltered_urls = list(set([x[0] for x in url]))
    list(set([x[0] for x in unfiltered_urls]))
    urls = []
    for i in range(len(unfiltered_urls)):
        if '][' in unfiltered_urls[i]:
            urls += unfiltered_urls[i].split('][')
        else:
            urls.append(unfiltered_urls[i])
    return urls
 
def respond(document):
    document = document.to_dict()
    user_subscription = db.collection('users').document(document['user_id']).get().to_dict()['subscription']
    instruct_limit = 0
    if user_subscription['type'] == 'free':
        instruct_limit = 2
    if user_subscription['type'] == 'basic':
        instruct_limit = 10
    if user_subscription['type'] == 'advanced':
        instruct_limit = 25
    if user_subscription['type'] == 'professional':
        instruct_limit = 100000
    if user_subscription['instruct'] >= instruct_limit:
        db.collection('advanced').document(
            str(document['id'])).update({'status': 'limit_reached'})
        return
    user_prompt = document['user_prompt']
    if get_token_count(user_prompt) > 1000:
        document['status'] = 'error'
        document['user_update'] = 'Your prompt is too long. Please try again with a shorter prompt.'
        db_update(document)
        return
    instructions = document['instructions']
    resource_ids = document['resource_ids']
    google_search = document['google_search']
    final_response = document['final_response']
    if 'user_update' not in document:
        document['user_update'] = ''
    urls = document['urls']
    document['status'] = 'in progress'
    document['name'] = give_a_name(user_prompt)
    db_update(document)
    if len(instructions) == 0:
        document['status'] = 'generating instructions'
        document['user_update'] = "Generating instructions..."
        db_update(document)
        list_of_instructions = getInstruction(user_prompt)
        instructions = [{'instruction': instruction, 'response': '', 'links': []} for instruction in list_of_instructions]
        document['instructions'] = instructions
        document['status'] = 'instructions generated' 
        db_update(document)
        document['name'] = give_a_name(user_prompt)
        db_update(document)
        return document
    do_instructions = False
    for i in range(len(instructions)):
        if instructions[i]['response'] == '':
            do_instructions = True
            break
    if do_instructions:
        document['status'] = 'generating instruction responses'
        document['user_update'] = "Generating instruction responses..."
        db_update(document)
        for i in range(len(instructions)):
            if i+1 > len(instructions):
                break
            if instructions[i]['response'] != '':
                continue
            document['status'] = 'generating instruction responses ' + str(i+1) + '/' + str(len(instructions))
            document['user_update'] = "Generating instruction responses " + str(i+1) + '/' + str(len(instructions))
            db_update(document)
            web = False
            if google_search == 'auto':
                document['user_update'] = "Determining whether to use the internet..."
                db_update(document)
                web = determineGoogleSearch(user_prompt, instructions[:i+1])
            if google_search == 'on':
                web = True
            if google_search == 'off':
                web = False
            result = {'pages': [], 'embeddings': [], 'links': []}
            if web == True:
                document['user_update'] = "Using the internet..."
                db_update(document)
                google_result = scrape_results(google_results(f"""Instruction chain we are following: {instructions}
                    Original prompt: {user_prompt}
                    Current instruction step: {instructions[i]['instruction']}""", document), document)
                result['pages'] += google_result['pages']
                result['embeddings'] += google_result['embeddings']
                result['links'] += google_result['links']
            if len(resource_ids) > 0:
                resource_result = scrape_resources(document['user_id'], resource_ids)
                result['pages'] += resource_result['pages']
                result['embeddings'] += resource_result['embeddings']
                result['links'] += resource_result['links']
            result = getBestResults(result['pages'], result['embeddings'], result['links'], instructions[i]['instruction'])
            instruction_result = write_instruction(document, i, result, instructions[i], instructions, user_prompt)
            instructions[i]['response'] = instruction_result
            links = findUrls(instruction_result)
            names = []
            db_update(document)
            for link in links:
                if link in urls:
                    names.append(urls[link])
                else:
                    names.append(name_a_url(link))
                    urls[link] = names[-1]
            document['urls'] = urls
            instructions[i]['links'] = [{'name': name, 'link': link} for name, link in zip(names, links)]
            document['instructions'] = instructions
            db_update(document)
        document['status'] = 'instruction responses generated'
        db_update(document)
        user_subscription['instruct'] += 1
        db.collection('users').document(str(document['user_id'])).update({'subscription': user_subscription})
        return document
    if final_response['response'] == '':
        document['status'] = 'generating final response'
        document['user_update'] = "Generating final response..."
        db_update(document)
        instructions_str = ''
        for i in instructions:
            instructions_str += i['instruction'] + '\n' + i['response'] + '\n'
        response = turbo(prompt = final_prompt.format(user_prompt=user_prompt, instructions=instructions_str), tokens=4000, model='gpt-4')
        complete_response = ''
        for resp in response:
            if 'content' not in resp['choices'][0]['delta']:
                continue
            complete_response += resp['choices'][0]['delta']['content']
            if len(complete_response) % 100 == 0 :
                document['final_response']['response'] = complete_response
                db_update(document)
        links = findUrls(complete_response)
        names = []
        document['final_response']['response'] = complete_response
        document['final_response']['links'] = []
        db_update(document)
        for link in links:
            if link in urls:
                names.append(urls[link])
            else:
                names.append(name_a_url(link))
                urls[link] = names[-1]
        document['urls'] = urls
        document['final_response']['response'] = complete_response
        document['final_response']['links'] = [{'name': name, 'link': link} for name, link in zip(names, links)]
        document['status'] = 'complete'
        db_update(document)
        document['name'] = give_a_name(final_response)
        return document
    return document

def on_snapshot(col_snapshots, changes, read_time):
    print(col_snapshots)
    for doc in col_snapshots:
        print(u'Received document snapshot: {}'.format(doc.id))
        respond(doc)

def thread(col_snapshots, changes, read_time):
    print("\n\n")
    print(u'Thread initialized')
    tz_chi = pytz.timezone('America/New_York')
    now = datetime.datetime.now(tz_chi)
    date_time = now.strftime("%Y-%m-%dT%H:%M:%S.%f")
    print("Current Time = ", date_time)
    threads = []
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
collection_query = db.collection(
    'advanced').where('status', '==', 'pending')
doc_watch = collection_query.on_snapshot(thread)
while True:
    time.sleep(1)