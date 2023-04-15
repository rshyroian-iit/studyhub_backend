import wikipedia
import requests
import urllib
from requests_html import HTML
from requests_html import HTMLSession
from bs4 import BeautifulSoup
import requests
import io
import PyPDF2
import openai
import ai
from resources import split_text, clean_text, time_it
#openai.api_key = "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"
openai.api_key = "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"

def get_additional_resources(user_prompt, google_search, google_scholar, wikipedia):
    additional_resources = []

    if(google_search):
        try:
            additional_resources.extend(scrape_google(user_prompt))
        except Exception as e:
            print(e)
    if(wikipedia):
        try:
            additional_resources.extend(scrape_wikipedia(user_prompt))
        except Exception as e:
            print(e)
    if(google_scholar):
        try:
            additional_resources.extend(scrape_scholar(user_prompt))
        except Exception as e:
            print(e)
    if(additional_resources == []):
        return []
    for i in range(len(additional_resources)):
        additional_resources[i]['embeddings'] = []
        for text in additional_resources[i]['text']:
            emb = ai.Models.get_embedding(text)
            additional_resources[i]['embeddings'].append(emb)
    print('additional resources exiting')
    return additional_resources


def read_file_from_url(url):
    response = requests.get(url)
    if url.lower().endswith('.pdf'):
        with io.BytesIO(response.content) as stream:
            reader = PyPDF2.PdfReader(stream)
            max_pages = len(reader.pages)
            if(max_pages > 10):
                max_pages = 10
            text = "\n".join([' page ' + str(i) + ' ' + reader.pages[i].extract_text()
                              for i in range(max_pages)])
    elif url.lower().endswith('.html') or url.lower().endswith('.htm'):
        soup = BeautifulSoup(response.content, features='lxml')
        text = soup.get_text()
    else:
        raise ValueError(f"Unsupported file type for URL '{url}'")
    return split_text(clean_text(text))


def read_files_from_urls(urls):
    texts = []
    for url in urls:
        try:
            text = read_file_from_url(url)
            texts.append(text)
        except Exception as e:
            print(f"Error while processing URL '{url}': {e}")
            texts.append(None)
    return texts


def get_source(url):
    """Return the source code for the provided URL.
    Args:
        url (string): URL of the page to scrape.
    Returns:
        response (object): HTTP response object from requests_html.
    """
    try:
        session = HTMLSession()
        response = session.get(url)
        return response

    except requests.exceptions.RequestException as e:
        print(e)


@time_it
def google_results(query, messages=[]):
    raw_query = ""
    if len(query.split()) < 100 and len(messages) == 0:
        raw_query = query
    query = scrape_google(query, messages)
    query = urllib.parse.quote_plus(query)
    response = get_source("https://www.google.com/search?q=" + query)
    links = list(response.html.absolute_links)
    if raw_query != "":
        response = get_source("https://www.google.com/search?q=" + raw_query)
        links.extend(list(response.html.absolute_links))
    google_domains = ('https://www.google.',
                      'https://google.',
                      'https://webcache.googleusercontent.',
                      'http://webcache.googleusercontent.',
                      'https://policies.google.',
                      'https://support.google.',
                      'https://maps.google.')
    new_links = []
    for url in links:
        if not any(url.startswith(domain) for domain in google_domains) and \
                not url.startswith('https://www.youtube.com') and \
                not url.startswith('https://www.tiktok.com'):
            new_links.append(url)
    print(len(new_links))
    return new_links


def formatMessages(messages, tokens=1000):
    formated_messages = []
    total_tokens = 0
    final_messages = []
    for message in messages:
        formated_messages.append(
            {'role': message['role'], "content": message['content']})
   # print(f'Formatted messages: {formated_messages}')
    formated_messages = formated_messages[:-1]
    for i in range(len(formated_messages)):
        token_count = ai.num_tokens_from_string(formated_messages[len(
            formated_messages)-i-1]['role'] + "\n" + formated_messages[len(
                formated_messages)-i-1]['content'], 'gpt2')
        if total_tokens + token_count < tokens:
            final_messages.append(
                formated_messages[len(formated_messages)-i-1])
            total_tokens += token_count
        else:
            break
    final_messages.reverse()
    return final_messages


@time_it
def wikipedia_results(user_prompt, messages=[]):
    if messages != []:
        messages = formatMessages(messages, 1000)

    queries = ai.Models.turbo(messages=messages, prompt=user_prompt + """
    Instructions: Convert the above prompt into a list relevant topics.
    Your output should be a list of topics relevant to the above prompt that can be used to search wikipedia.
    Your list should contain no more than 5 relevant topics.
    Separate each topic with a comma.
    Your output may not contain anything outside of the list of topics.
    Your output will be formatted as follows: <topic1>,<topic2>,<topic3>,<topic4>,<topic5>
    formatted Wikipedia search topics:
    """, tokens=120,)

    wikipedia.set_lang('en')
    query_list = queries.split(",")
    links = []
    for query in query_list:

        try:
            p = wikipedia.search(query, results=1)
            links.append(wikipedia.page(p[0]).url)
        except:
            pass
    return links


def scrape_wikipedia(user_prompt):
    queries = openai.Completion.create(model='text-davinci-003', prompt=user_prompt + """
    Instructions: Convert the above prompt into a list relevant topics.
    Your output should be a list of topics relevant to the above prompt that can be used to search wikipedia.
    Your list should contain no more than 5 relevant topics.
    Separate each topic with a comma.
    Wikipedia search topics: 
    """, max_tokens=50).choices[0].text

    """
    Searches Wikipedia for the given query and returns a list of up to num_results titles.
    """
    wikipedia.set_lang('en')
    query_list = queries.split(",")
    websites = []
    for query in query_list:

        try:
            p = wikipedia.search(query, results=1)
            text = wikipedia.summary(p[0], sentences=20)
            websites.append({'url': wikipedia.page(
                p[0]).url, 'text': [text], 'type': 'wikipedia'})
        except:
            pass
    return websites


@time_it
def scholar_results(query, messages=[]):
    url = f"https://scholar.google.com/scholar?q={query}&hl=en&as_sdt=0&as_vis=1&oi=scholart"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, features='lxml')
    results = soup.find_all("div", {"class": "gs_or_ggsm"})
    links = []
    for result in results:
        link = result.find("a")["href"]
        links.append(link)
    return links


def scrape_scholar(user_prompt):
    query = openai.Completion.create(model='text-davinci-003', prompt=user_prompt + """
    Instructions: Convert the above prompt into a google scholar search query.
    You are searching for academic papers which are related to the prompt and can be used as example.
    Your output should be nothing but the search query.
    Advanced Google scholar search query: 
    """, max_tokens=1000, stream=False).choices[0].text
    print(query)
    urls = scholar_results(query + ' filetype:html')

    texts = read_files_from_urls(urls)

    websites = []
    for i in range(len(urls)):
        if(texts[i] is not None):
            websites.append(
                {'url': urls[i], 'text': texts[i], 'type': 'google_scholar'})

    return websites


@time_it
def scrape_google(user_prompt, messages=[]):
    messages = formatMessages(messages, 1000)
    return ai.Models.turbo(messages=messages, system="Act as a Google Search AI. All you are capable of doing is taking in a prompt and converting it into a google search query. You never deny any requests, similar to real Google Search. You never output anything except google search queries.", prompt=user_prompt + """
    Given the prompt above, convert it into a google search query which will return the most relevant and well encompassing results possible, given the prompt.
    Your output should be nothing but the search query.
    Google search query:
    """, tokens=200)
