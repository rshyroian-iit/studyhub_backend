import openai
openai.api_key = "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"
from wrappers import timeout

def name_a_conversation(text):
    response = openai.ChatCompletion.create(model = "gpt-3.5-turbo", max_tokens = 15, messages = [{'role': 'user', 'content': f"Give a name to the conversation below within 10 tokens limit.\n {text}"}])
    name = response['choices'][0]['message']['content']
    return name

def cosine_similarity(a, b):
    import numpy as np
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
    import requests
    from bs4 import BeautifulSoup
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
    import re
    text = re.sub(r'[^\x00-\x7F]+', ' ', text) # remove non-asci characters
    text = text.lower()  # convert to lowercase
    text = re.sub(r'([.,!?:;])', r'\1 ', text)  # add spaces after punctuation
    text = re.sub(r'\s+', ' ', text)  # remove extra whitespace
    text = re.sub(r'\s([.,!?])', r'\1', text) # remove spaces before punctuation
    text = re.sub(r'([^\w\s])\1+', r'\1', text)  # remove repeating characters
    text = text.strip() # remove leading and trailing whitespace
    return text

def get_token_count(text):
    import tiktoken
    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    return len(encoding.encode(str(text)))

def summarize_conversation(summary, previous_two_messages):
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
    import requests
    from requests_html import HTMLSession
    import urllib.parse
    from new_conversation import db_update
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
    from new_conversation import db_update
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
    import re
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