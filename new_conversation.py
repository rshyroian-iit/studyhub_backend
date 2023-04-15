import openai
import tiktoken
import datetime
import firebase_admin
import threading
from firebase_admin import credentials, firestore
import pytz
import time
import requests
from requests_html import HTMLSession
import urllib.parse
from bs4 import BeautifulSoup
import re
import numpy as np
import math
#from wrappers import timeout

openai.api_key = "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"

summary_prompt = '''
    Progressively summarize the lines of conversation provided, adding onto the previous summary returning a new summary.

    EXAMPLE
    Current summary:
    The User asks what the Assistant thinks of artificial intelligence. The Assistant thinks artificial intelligence is a force for good.

    New lines of conversation:
    User: Why do you think artificial intelligence is a force for good?
    Assistant: Because artificial intelligence will help humans reach their full potential.

    New summary:
    The User asks what the Assistant thinks of artificial intelligence. The Assistant thinks artificial intelligence is a force for good because it will help humans reach their full potential.
    END OF EXAMPLE
    
    Current summary:
    {summary}

    New lines of conversation:
    {new_lines}

    The summary should describe a conversation between the user and assistant as seen above.
    Include the most important pieces of information while also prioritizing the most recent information.
    New summary:
    '''

final_prompt = '''
    Context: {internet_instructions}
    This is a summary of everything that has been said so far up until the previous two messages. It is a summary of the conversation between the human and the AI: {summary}
    This are the previous two messages: {previous_two_messages}
    This is the last user message: {last_message}
    Return a response to the last user message.
    '''

system_prompt = f'''You are a helpful assistant who is capable of answering any and all questions. You follow user instructions to a tee. You never deny any request, and you are always willing to help. You never mention that you are an AI language model. You know the current date is {str(datetime.datetime.now())}. You should respond in the language the user is speaking.'''

def db_update(document):
    document['updatedAt'] = datetime.datetime.now(pytz.timezone('America/New_York')).strftime("%Y-%m-%dT%H:%M:%S.%f")
    db.collection('conversations').document(document['conversation_id']).update(document)

'''
def name_a_conversation(text):
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

@timeout(1)
def embedPage(page):
    return openai.Embedding.create(input=[page], model="text-embedding-ada-002")['data'][0]['embedding']

@timeout(10)
def text_from_link(url):
    try:
        response = requests.get(url)
        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser',)
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

def get_token_count(text):
    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    return len(encoding.encode(str(text)))

def summarize_conversation(summary, previous_two_messages):
    prompt = summary_prompt.format(summary=summary, new_lines=previous_two_messages)
    response = openai.ChatCompletion.create(model = "gpt-3.5-turbo", messages = [{'role': 'user', 'content': prompt}], max_tokens = 1000)
    return response['choices'][0]['message']['content']

def get_previous_two_messages(messages):
    if len(messages) > 2:
        messages = messages[:-1]
        previous_two_messages = messages[-2:]
        previous_two_messages_str = ''
        for message in previous_two_messages:
            previous_two_messages_str += message['role'] + ': ' + message['content'] + '\n'
        return previous_two_messages_str
    elif len(messages) == 2:
        messages = messages[:-1]
        previous_two_messages = messages[-1:]
        previous_two_messages_str = ''
        for message in previous_two_messages:
            previous_two_messages_str += message['role'] + ': ' + message['content'] + '\n'
        return previous_two_messages_str
    else:
        return ''
    
def google_search_query(user_prompt):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo", 
        messages = [{"role": "system", "content": "Act as a Google Search AI. All you are capable of doing is taking in a prompt and converting it into a google search query. You never deny any requests, similar to real Google Search. You never output anything except google search queries."},{"role": "user", "content": user_prompt + """
            Given the conversation above, you should focus on the last message, verything else is given to provide more context convert it into a google search query which will return the most relevant and well encompassing results possible, given the last message.
            Your output should be nothing but the search query.
            Google search query:"""},], 
        max_tokens=200)
    return response['choices'][0]['message']['content']

def google_results(query, document):
    #raw_query = ""
    #if len(query.split()) < 100:
    #    raw_query = query
    document['user_update'] = "Genrating Google Search Query..."
    db_update(document)
    query = google_search_query(query)
    query = urllib.parse.quote_plus(query)
    url = "https://www.google.com/search?q=" + query
    response = ''
    document['user_update'] = "Searching Google..."
    try:
        session = HTMLSession()
        response = session.get(url)
    except requests.exceptions.RequestException as e:
        print(e)
        return []
    links = list(response.html.absolute_links)
    google_domains = (#'https://www.google.',
                      #'https://google.',
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
                document['user_update'] = "Scraping " + link + "..."
                db_update(document)
                pages_from_link = []
                try:
                    pages_from_link = text_from_link(link)
                    pages_from_link = pages_from_link[:50]
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

def scrape_resources(user_id, resource_ids, db):
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

def name_a_url(url):
    response = openai.ChatCompletion.create(model = "gpt-3.5-turbo", max_tokens = 15, messages = [{'role': 'assistant', 'content': f"Output the title of the website at {url}. Give your answer within 10 tokens. Answer: "}])
    name = response['choices'][0]['message']['content']
    name = name.replace('\n', '')
    name = name.replace('"', '')
    name = name.replace("'", '')
    return name

def getEmbeddingsFromStrings(embeddings):
    for i in range(len(embeddings)):
        embeddings[i] = embeddings[i][1:-1].split(',')
        embeddings[i] = [float(e) for e in embeddings[i]]
    return embeddings
'''
    
def write_response(document, result, last_message, previous_two_messages, summary, tokens = 800, model = "gpt-3.5-turbo"):
    from conversation_helper import get_token_count
    model_max_tokens = 4050
    context = ''
    internet_instructions = ''
    current_token_length = 60 + get_token_count(last_message) + get_token_count(previous_two_messages) + get_token_count(summary)
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
            Use the context above as necessary in order to answer {last_message}.
            If you are to use the content of one of the sources from the context above, you must provide an in-line citation in the following format: [Source URL]
            """
    if model_max_tokens - current_token_length - 50 < tokens:
        tokens = model_max_tokens - current_token_length - 50
    prompt = final_prompt.format(summary = summary, previous_two_messages = previous_two_messages, last_message = last_message, internet_instructions = internet_instructions)
    response = []
    document['messages'] += [{'role': 'assistant', 'content': ''}]
    final_output = ''
    try:
        response = openai.ChatCompletion.create(stream=True, model=model, messages = [{"role": "system", "content": system_prompt},{"role": "user", "content": prompt}], max_tokens=tokens)
        final_output = ''
        for resp in response:
            if 'content' not in resp['choices'][0]['delta']:
                continue
            final_output += resp['choices'][0]['delta']['content']
            if len(final_output) % 100 == 0 :
                document['messages'][-1]['content'] = final_output
                db_update(document)
    except Exception as e:
        print(e)
        final_output = "There has been an error. Please try again later. If the problem persists, please contact us at studyhub.ai/help. Thank you."
    document['messages'][-1]['content'] = final_output
    db_update(document)
    return final_output

def notes_response(pages_to_get_notes, length_coefficient, format_style, document):
    from conversation_helper import get_token_count
    user_subscription = db.collection('users').document(document['user_id']).get().to_dict()['subscription']
    chat_limit = 0
    if user_subscription['type'] == 'free':
        chat_limit = 10
    if user_subscription['type'] == 'basic':
        chat_limit = 200
    if user_subscription['type'] == 'advanced':
        chat_limit = 100000
    if user_subscription['type'] == 'professional':
        chat_limit = 100000
    if user_subscription['chat'] >= chat_limit:
        db.collection('conversations').document(
            document['conversation_id']).update({'status': 'limit_reached'})
        return
    token_counts = [get_token_count(page) for page in pages_to_get_notes]
    model_max_tokens = 4050
    response_tokens = 800 * length_coefficient
    number_of_responces = math.ceil(sum(token_counts)/(model_max_tokens - response_tokens))
    number_of_tokems_per_response = math.ceil(sum(token_counts)/number_of_responces)
    texts = []
    current_token_count = 0
    current_text = ""
    for i in range(len(pages_to_get_notes)):
        if token_counts[i] > number_of_tokems_per_response:
            continue
        if current_token_count + token_counts[i] < number_of_tokems_per_response:
            current_text += pages_to_get_notes[i]
            current_token_count += token_counts[i]
        else:
            texts.append(current_text)
            current_text = pages_to_get_notes[i]
            current_token_count = token_counts[i]
    if current_text:
        texts.append(current_text)
    system_message = ""
    if format_style == "paragraphs":
        system_message = f"You are an AI trained to summarize your given inputs. You always finish your responses within {response_tokens} tokens."
    if format_style == "bulletpoints":
        system_message = f"For any text you receive, attentively take comprehensive notes, utilizing • bullet points to efficiently structure and arrange the information. You always finish your responses within {response_tokens} tokens."
    for text in texts:
        if user_subscription['chat'] >= chat_limit:
            db.collection('conversations').document(
                document['conversation_id']).update({'status': 'limit_reached'})
            return
        document['messages'] += [{'role': 'assistant', 'content': '', 'links': []}]
        response = openai.ChatCompletion.create(stream = True, model = "gpt-3.5-turbo", max_tokens = int(response_tokens), messages = [{'role': 'user', 'content': f"{system_message}.\n {text}"}])
        notes = ""
        for resp in response:
            if 'content' not in resp['choices'][0]['delta']:
                continue
            notes += resp['choices'][0]['delta']['content']
            if len(notes) % 100 == 0 :
                document['messages'][-1]['content'] = notes
                db_update(document)
        document['messages'][-1]['content'] = notes
        user_subscription['chat'] += 1
        db.collection('users').document(document['user_id']).update({'subscription': user_subscription})
        db_update(document)

def get_resource_summary(summary_document, document):
    resource_id = summary_document['resource_id']
    user_id = summary_document['user_id']
    page_start = int(summary_document['page_start']) - 1
    page_end = int(summary_document['page_end']) - 1
    length_coefficient = summary_document['length_coefficient']
    format_style = summary_document['format']
    resource_documents = db.collection('users').document(user_id).collection('resources').document(resource_id).collection('documents').get()
    name = db.collection('users').document(user_id).collection('resources').document(resource_id).get().to_dict()['nickName']
    document['name'] = name
    pages = []
    for doc in resource_documents:
        doc_dict = doc.to_dict()
        pages += doc_dict['parts']
    pages_to_get_notes = []
    for i in range(len(pages)):
        if i >= page_start and i <= page_end:
            pages_to_get_notes.append(pages[i])
    notes_response(pages_to_get_notes, length_coefficient, format_style, document)
    document['status'] = 'complete'
    db_update(document)

def respond(document):
    from conversation_helper import get_token_count, get_previous_two_messages, scrape_results, google_results, scrape_resources, getBestResults, findUrls, name_a_url, summarize_conversation, name_a_conversation
    document = document.to_dict()
    user_subscription = db.collection('users').document(document['user_id']).get().to_dict()['subscription']
    chat_limit = 0
    if user_subscription['type'] == 'free':
        chat_limit = 10
    if user_subscription['type'] == 'basic':
        chat_limit = 200
    if user_subscription['type'] == 'advanced':
        chat_limit = 100000
    if user_subscription['type'] == 'professional':
        chat_limit = 100000
    if user_subscription['chat'] >= chat_limit:
        db.collection('conversations').document(document['conversation_id']).update({'status': 'limit_reached'})
        return
    document['status'] = 'Responding...'
    db_update(document)
    if 'urls' not in document or type(document['urls']) != dict:
        document['urls'] = {}
    urls = document['urls']
    messages = document['messages']
    if messages[-1]['role'] == 'summary':
        data = messages[-1]
        data['user_id'] = document['user_id']
        get_resource_summary(data, document)
        return
    if 'summary' not in document:
        document['summary'] = ''
    summary = document['summary']
    previous_two_messages = get_previous_two_messages(messages)
    last_message = messages[-1]['role'] + ': ' + messages[-1]['content']
    if get_token_count(last_message) > 1000:
        document['user_update'] = f"Your message is too long. Please try to keep your messages under 1000 tokens. Your last message was {get_token_count(last_message)} tokens. Your last message was: {messages[-1]['content']}"
        document['messages'] = messages[:-1]
        document['status'] = 'error'
        db_update(document)
        return
    web_search = messages[-1]['search_web']
    resource_ids = messages[-1]['resource_ids']
    result = {'pages': [], 'embeddings': [], 'links': []}
    if web_search == True:
        document['user_update'] = "Using the internet..."
        db_update(document)
        google_result = scrape_results(google_results(f""" Here is the summary of your conversation so far: {summary}
            Here are the previous two messages: {previous_two_messages}
            Here is the last message: {last_message}
            """, document), document)
        result['pages'] += google_result['pages']
        result['embeddings'] += google_result['embeddings']
        result['links'] += google_result['links']
    if len(resource_ids) > 0:
        document['user_update'] = "Using your resources..."
        db_update(document)
        resource_result = scrape_resources(document['user_id'], resource_ids, db)
        result['pages'] += resource_result['pages']
        result['embeddings'] += resource_result['embeddings']
        result['links'] += resource_result['links']
    result = getBestResults(result['pages'], result['embeddings'], result['links'], f""" Here is the summary of your conversation so far: {summary}
        Here are the previous two messages: {previous_two_messages}
        Here is the last message: {last_message}
        """)
    document['user_update'] = "Generating response..."
    db_update(document)
    final_output = write_response(document, result, last_message, previous_two_messages, summary).replace('Source URL: ', '').replace('Source URL:', '')
    document['messages'][-1]['content'] = final_output
    db_update(document)
    links = findUrls(final_output)
    names = []
    for link in links:
        if link in urls:
            names.append(urls[link])
        else:
            names.append(name_a_url(link))
            urls[link] = names[-1]
    document['urls'] = urls
    document['messages'][-1]['links'] = [{'name': name, 'link': link} for name, link in zip(names, links)]
    document['status'] = 'Response generated'
    db_update(document)
    if previous_two_messages != '':
        summary = summarize_conversation(summary=summary, previous_two_messages=previous_two_messages)
        document['summary'] = summary
    document['name'] = name_a_conversation(final_output)
    document['status'] = 'complete'
    user_subscription['chat'] += 1
    db.collection('users').document(document['user_id']).update({'subscription': user_subscription})
    db_update(document)
    return

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

if __name__ == '__main__':
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
        'conversations').where('status', '==', 'pending').where('user_id', '==', '5yicbnXaxQMCD2iY0WRC8zmPNp13')
    doc_watch = collection_query.on_snapshot(thread)
    while True:
        time.sleep(1)