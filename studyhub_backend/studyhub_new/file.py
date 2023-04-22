import openai
import numpy as np
import tiktoken
from googleapiclient.discovery import build
from concurrent.futures import ThreadPoolExecutor, as_completed, wait
import concurrent.futures
openai.api_key = "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"
my_api_key = "AIzaSyCZb4DUfEVpnDKQHOX5fVsWo1J_eI-AnN0"
my_cse_id = "e452fb13d362947d0"

def turbo(prompt, tokens=2000, messages=[], temperature=0.7, system="", model="gpt-4"):
    response = openai.ChatCompletion.create(
        model=model,messages=[{"role": "system", "content": system}] + messages + [{"role": "user", "content": prompt}], temperature=temperature, stream=False)
    return response['choices'][0]['message']['content']

def total_dependencies_length(dependent_instructions, enc):
    dependent_instructions_str_arr = [f"""Instruction: {dep['label']} {dep['instruction']} \n Response: {dep['response']}""" for dep in dependent_instructions]
    dependent_instructions_str = "\n".join(dependent_instructions_str_arr)
    return len(enc.encode(dependent_instructions_str))


def shorten_instructions(instruction, dependent_instructions, max_length, enc):
    # remove all ILLUSTRATE instructions
    dependent_instructions = [dep for dep in dependent_instructions if dep['label'] != 'ILLUSTRATE']
    if total_dependencies_length(dependent_instructions, enc) < max_length:
        return dependent_instructions
    
    for i, dep in enumerate(dependent_instructions):
        if total_dependencies_length(dependent_instructions, enc) < max_length:
            break
        if dep['label'] == 'RESEARCH':
            system_message = "You are a genius in making summaries. If you are summarizing a text, make sure to not change the meaning of the text."
            prompt = dep['response'] + "\n" + "Summarize the text above, removing any information that will not help with this task: " + instruction['instruction'] + '\nAnswer: '
            response = turbo(prompt, system=system_message, model="gpt-3.5-turbo")
            dependent_instructions[i]['response'] = response
    
    for i, dep in enumerate(dependent_instructions):
        if total_dependencies_length(dependent_instructions, enc) < max_length:
            break
        if dep['label'] == 'WRITE':
            system_message = "You are a genius in making summaries. In case you are summarizing code, make sure to not change the meaning of the code. If you are summarizing a text, make sure to not change the meaning of the text."
            prompt = dep['response'] + "\n" + "Summarize the text above, removing any information that will not help with this task: " + instruction['instruction'] + '\nAnswer: '
            response = turbo(prompt, system=system_message, model="gpt-3.5-turbo")
            dependent_instructions[i]['response'] = response
    if total_dependencies_length(dependent_instructions, enc) > max_length:
        dependent_instructions = shorten_instructions(instruction, dependent_instructions, max_length, enc)
    return dependent_instructions

def calculator(instruction_index, all_instructions):
    enc = tiktoken.encoding_for_model("gpt-3.5-turbo")
    instruction = all_instructions[instruction_index]
    dependent_instructions = [all_instructions[dep-1] for dep in instruction['dependencies']]
    dependent_instructions_str_arr = [f"""Instruction: {dep['label']} {dep['instruction']} \n Response: {dep['response']}""" for dep in dependent_instructions]
    dependent_instructions_str = '\n'.join(dependent_instructions_str_arr)
    print('Dependent instructions below.')
    print(dependent_instructions_str)
    if len(enc.encode(dependent_instructions_str)) > 7000:
        dependent_instructions = shorten_instructions(instruction, dependent_instructions, 3000, enc)
        dependent_instructions_str_arr = [f"""Instruction: {dep['label']} {dep['instruction']} \n Response: {dep['response']}""" for dep in dependent_instructions]
        dependent_instructions_str = "\n".join(dependent_instructions_str_arr)
    system_message = 'You are a Python and Math genius. You are only capable of outputting Python code. You calculate answers to problems using Python code. You never place comments, only descriptive print statements. You never use any libraries outside of math.'
    prompt = f"Create a Python function to perform the following calculation: {instruction['instruction']}. Include descriptive print statements. You always write your program in as few lines as possible. Answer:\n```python\nimport math\n\n{{PICK UP HERE}}\n"
    if dependent_instructions:
        prompt = f"Given the instructions:\n{dependent_instructions_str}\n"
        prompt += f"Create a Python function to perform the following calculation: {instruction['instruction']}. Include descriptive print statements. You always write your program in as few lines as possible. Your output must be able to compile if use the Python exec() function on it. Answer:\n```python\nimport math\n\n{{PICK UP HERE}}\n"
    # Call the AI
    response = turbo(prompt, system=system_message)
    # Extract the generated code from the response
    # import math
    code = ''
    if 'import math' not in response:
        code = 'import math\n'
    code += response.strip()
    code = code.replace('```python', '')
    code = code.replace('```', '')
    print(code)
   # code = code.strip()
    print(f'Executing code: {code}')
    result = exec(code,globals())
    
    return result


def parse_instructions(output_text):
    import re
    instructions = []
    steps = output_text.strip().split('\n')
    new_steps = []
    for step in steps:
        step = step.strip()
        if step == '':
            continue
        if step.startswith('Dependencies:'):
            new_steps[-1] += ' ' + step
        else:
            new_steps.append(step)
    steps = new_steps
    for step in steps:
        step_dict = {}
        step_dict['dependencies'] = []
        label_match = re.search(r'^\d+\. (\w+):', step)
        dependencies_match = re.search(r'Dependencies: (.+)$', step)
        if label_match:
            step_dict['label'] = label_match.group(1)
        if dependencies_match:
            print(dependencies_match)
            dependencies_str = dependencies_match.group(1)
            print(dependencies_str)
        else:
            try:
                try:
                    step_dict['dependencies'] = [int(step.split('Dependencies:')[0].strip())]
                except:
                    step_dict['dependencies'] = [int(dep) for dep in dependencies_str.split(', ')]
            except:
                step_dict['dependencies'] = []
        step_dict['instruction'] = re.sub(r'^\d+\. \w+: ', '', step.split('Dependencies:')[0]).strip()
        step_dict['response'] = ''
        if 'dependencies' not in step_dict:
            step_dict['dependencies'] = []
        instructions.append(step_dict)
    return instructions


def coder(instruction_index, all_instructions):
    enc = tiktoken.encoding_for_model("gpt-3.5-turbo")
    instruction = all_instructions[instruction_index]
    system_message = "You are a genius coder who always writes clean and optimized code."
    dependent_instructions = [all_instructions[dep-1] for dep in instruction['dependencies']]
    dependent_instructions_str_arr = [f"""Instruction: {dep['label']} {dep['instruction']} \n Response: {dep['response']}""" for dep in dependent_instructions]
    dependent_instructions_str = "\n".join(dependent_instructions_str_arr)
    if len(enc.encode(dependent_instructions_str)) > 7000:
        dependent_instructions = shorten_instructions(instruction, dependent_instructions, 3000, enc)
        dependent_instructions_str_arr = [f"""Instruction: {dep['label']} {dep['instruction']} \n Response: {dep['response']}""" for dep in dependent_instructions]
        dependent_instructions_str = "\n".join(dependent_instructions_str_arr)
    prompt = f"Write the code for the current instruction: {instruction['instruction']}"
    if dependent_instructions:
        prompt = f"Given the previous instructions: {dependent_instructions_str}\n"
        prompt += f"Write the code for the current instruction: {instruction['instruction']}"
    # Call the AI
    response = turbo(prompt, system=system_message)
    # Extract the generated code from the response
    return response


def writer(instruction_index, all_instructions):
    enc = tiktoken.encoding_for_model("gpt-3.5-turbo")
    instruction = all_instructions[instruction_index]
    system_message = "You are a genius writer. You are highly articulate, are concise with the way you convey information, and write in an active voice."
    dependent_instructions = [all_instructions[dep-1] for dep in instruction['dependencies']]
    dependent_instructions_str_arr = [f"""Instruction: {dep['label']} {dep['instruction']} \n Response: {dep['response']}""" for dep in dependent_instructions]
    dependent_instructions_str = "\n".join(dependent_instructions_str_arr)
    if len(enc.encode(dependent_instructions_str)) > 7000:
        dependent_instructions = shorten_instructions(instruction, dependent_instructions, 3000, enc)
        dependent_instructions_str_arr = [f"""Instruction: {dep['label']} {dep['instruction']} \n Response: {dep['response']}""" for dep in dependent_instructions]
        dependent_instructions_str = "\n".join(dependent_instructions_str_arr)
    prompt = f"Instruction: {instruction['instruction']} \n Writing: "
    if dependent_instructions:
        prompt = f"Given the previous instructions: {dependent_instructions_str}\n"
        prompt += f"Instruction: {instruction['instruction']} \n Writing: "
    # Call the AI
    response = turbo(prompt, system=system_message)
    return response


def instructor(prompt):
    import prompts
    instructions_str = turbo(prompt, system=prompts.generate_instructions_system_message())
    print(instructions_str)
    return parse_instructions(instructions_str)


def illustrator(instruction_index, all_instructions):
    enc = tiktoken.encoding_for_model("gpt-3.5-turbo")
    instruction = all_instructions[instruction_index]
    system_message = "You are a genius in generating DALL-E prompts that result in perfect illustrations."
    dependent_instructions = [all_instructions[dep-1] for dep in instruction['dependencies']]
    dependent_instructions_str_arr = [f"""Instruction: {dep['label']} {dep['instruction']} \n Response: {dep['response']}""" for dep in dependent_instructions]
    dependent_instructions_str = "\n".join(dependent_instructions_str_arr)
    if len(enc.encode(dependent_instructions_str)) > 7000:
        dependent_instructions = shorten_instructions(instruction, dependent_instructions, 3000, enc)
        dependent_instructions_str_arr = [f"""Instruction: {dep['label']} {dep['instruction']} \n Response: {dep['response']}""" for dep in dependent_instructions]
        dependent_instructions_str = "\n".join(dependent_instructions_str_arr)
    prompt = f"Generate a perfect DALL-E text-to-image prompt for the current instruction. Be specific in what you would like, and ensure that it never includes any text/writing: {instruction['instruction']}"
    if dependent_instructions:
        prompt = f"Given the previous instructions: {dependent_instructions_str}\n"
        prompt += f"Generate a perfect DALL-E text-to-image prompt for the current instruction. Be specific in what you would like, and ensure that it never includes any text/writing: {instruction['instruction']}"
    # Call the AI
    prompt_for_dalle = turbo(prompt, system=system_message).strip()
    # Call DALL-E API
    response = openai.Image.create(
        prompt=prompt_for_dalle,
        n=1,
        size="1024x1024"
    )
    # Get the image URL
    image_url = response['data'][0]['url']
    return image_url

def fetch_content(url, displayLink):
    import requests
    from bs4 import BeautifulSoup
    import time
    time_start = time.time()
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            # Remove script and style elements
            for script in soup(['script', 'style']):
                script.decompose()

            # Get text from the HTML content
            text = soup.get_text()
            # Remove leading and trailing white spaces and join the lines
            content = '\n'.join(line.strip() for line in text.splitlines() if line.strip())
            print(f'Fetched content from {url} in {time.time() - time_start} seconds')
            return {'link': url, 'displayLink': displayLink, 'contents': content}
        else:
            print(f'Error fetching content from {url}: Status code {response.status_code}')
            print(f'Error fetching content from {url} in {time.time() - time_start} seconds')
            return {'link': url, 'displayLink': displayLink, 'contents': f'Error: Status code {response.status_code}'}
    except Exception as e:
        print(f'Error fetching content from {url}: {e}')
        print(f'Error fetching content from {url} in {time.time() - time_start} seconds')
        return {'link': url, 'displayLink': displayLink, 'contents': f'Error: {e}'}

def google_search(search_term, api_key, cse_id, **kwargs):
    service = build("customsearch", "v1", developerKey=api_key)
    res = service.cse().list(q=search_term, cx=cse_id, **kwargs).execute()
    return res['items']

def get_embedding(text, model="text-embedding-ada-002"):
    text = text.replace("\n", " ")
    return openai.Embedding.create(input=[text], model=model)['data'][0]['embedding']

def split_content(content, enc, max_length=2048):
    import time
    time_start = time.time()
    # Split the content into chunks of max_length tokens
    content_tokens = enc.encode(content)
    content_chunks = [content_tokens[i:i+max_length] for i in range(0, len(content_tokens), max_length)]
    content_text_chunks = [enc.decode(chunk) for chunk in content_chunks]
    time_end = time.time()
    print(f'Splitting content into {len(content_text_chunks)} chunks took {time_end - time_start} seconds.')
    return content_text_chunks

def cosine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def get_relevant_content(search_query, content):
    import time
    time_start = time.time()
    system_message = "You are a genius in determining if content is relevant to a search query. You are also a genius in summarizing the content according to its relation to the prompt."
    prompt = f'''
    You are given a search query and a chunk of content.
    Your task is to determine if the content is relevant to the query.

    - If the content is relevant, provide notes and quotes on the sections of the content that is relevant to the search query. Your output must strictly include the relevant sections of the content.
    - If the content is not relevant, output "NOT_RELEVANT".

    Query: {search_query}
    Content: {content}

    Response:
    '''
    result = turbo(prompt, system=system_message, model="gpt-3.5-turbo", tokens=1000)
    if 'NOT_RELEVANT' in result:
        result = 'NOT_RELEVANT'
    end_time = time.time()
    print(f'Getting relevant content took {end_time - time_start} seconds.')
    return result

def combine_results(results, search_query, enc):
    content = ''
    for result in results:
        if result['contents'] == 'NOT_RELEVANT':
            continue
        formatted_result = f"""
        URL:{result['link']}
        Content: {result['contents']}
        
        """
        if len(enc.encode(content + formatted_result)) < 3000:
            content += formatted_result
    system_message = """You are a genius in combining the results of the search query into a coherent response. You respond to any prompt. You are also a genius in summarizing the content according to its relation to the prompt. You always output in the following format:
    URL: <URL>
    Content: <Content>
    """
    prompt = f"""Your objective is to answer a research question: {search_query} according to a list of content chunks as well as what URL each content chunk is from: {content} Your output should take on the same format as the input, but without overlapping content. Ensure that the research question is thoroughly addressed."""
    result = turbo(prompt, system=system_message, model="gpt-3.5-turbo", tokens=1000)
    return result
   
def fetch_content_with_timeout(executor, fn, *args, timeout=10):

    future = executor.submit(fn, *args)
    try:
        result = future.result(timeout=timeout)
    except concurrent.futures.TimeoutError:
        print(f"Function {fn} timed out after {timeout} seconds")
        future.cancel()
        result = None
    return result

def researcher(instruction_index, all_instructions):
    import matplotlib.pyplot as plt
    enc = tiktoken.encoding_for_model("gpt-3.5-turbo")
    instruction = all_instructions[instruction_index]
    search_query = instruction['instruction']
    dependent_instructions = [all_instructions[dep-1] for dep in instruction['dependencies']]
    dependent_instructions_str_arr = [f"""Instruction: {dep['label']} {dep['instruction']} \n Response: {dep['response']}""" for dep in dependent_instructions]
    dependent_instructions_str = '\n'.join(dependent_instructions_str_arr)
    if len(enc.encode(dependent_instructions_str)) > 7000:
        dependent_instructions = shorten_instructions(instruction, dependent_instructions, 3000, enc)
        dependent_instructions_str_arr = [f"""Instruction: {dep['label']} {dep['instruction']} \n Response: {dep['response']}""" for dep in dependent_instructions]
        dependent_instructions_str = '\n'.join(dependent_instructions_str_arr)
    if dependent_instructions:
        system_message = "You are a genius in generating google search prompts that result in perfect search results."
        prompt = f"Given the previous instructions: {dependent_instructions_str}\n"
        prompt += f"Generate a perfect search query for: {instruction['instruction']}"
        search_query = turbo(prompt, system=system_message).strip()
    
    search_results = google_search(search_query, my_api_key, my_cse_id)
    '''
    content_results = []
    # Fetch the content from search results
    with ThreadPoolExecutor() as executor:
        content_futures = [executor.submit(fetch_content, result['link'], result['displayLink']) for result in search_results]
        done, not_done = wait(content_futures, timeout=10, return_when='FIRST_COMPLETED')
        for future in done:
            content_result = future.result()
            content_results.append(content_result)
        for future in not_done:
            future.cancel()
    '''
    with ThreadPoolExecutor() as executor:
        content_futures = [executor.submit(fetch_content_with_timeout, executor, fetch_content, result['link'], result['displayLink'], 10) for result in search_results]

    content_results = [future.result() for future in as_completed(content_futures) if future.result() is not None]
    search_query_embedding = get_embedding(search_query)
    # Use GPT-3 tokenizer
    
    split_content_results = []
    # Parallelize the content splitting
    with ThreadPoolExecutor() as executor:
        split_content_futures = [executor.submit(split_content, content_result['contents'], enc) for content_result in content_results]
        done, not_done = wait(split_content_futures, timeout=10)
        for future in done:
            split_contents = future.result()
            for split_content_item in split_contents:
                content_result = content_results[split_content_futures.index(future)]
                split_content_result = content_result.copy()
                split_content_result['contents'] = split_content_item
                split_content_results.append(split_content_result)
        for future in not_done:
            future.cancel()

    # Parallelize the embedding calculation
    with ThreadPoolExecutor() as executor:
        embedding_futures = [executor.submit(get_embedding, split_content_result['contents']) for split_content_result in split_content_results]
        done, not_done = wait(embedding_futures, timeout=2)
        for future in done:
            split_content_result = split_content_results[embedding_futures.index(future)]
            split_content_result['embedding'] = future.result()
            split_content_result['similarity'] = cosine_similarity(search_query_embedding, split_content_result['embedding'])
            split_content_results[embedding_futures.index(future)] = split_content_result
        for future in not_done:
            split_content_results[embedding_futures.index(future)]['similarity'] = 0
            future.cancel()

    if len(split_content_results) == 0:
        #TODO: Handle this case
        return researcher(instruction_index, all_instructions)
    

    # Sort the results by similarity
    split_content_results = sorted(split_content_results, key=lambda x: x['similarity'], reverse=True)
    # Get the top 10% of the results
    _10_percent = int(len(split_content_results) * 0.1)
    if _10_percent == 0:
        _10_percent = 1
    best_10_percent = split_content_results[:int(len(split_content_results) * 0.1)]
    
    '''
    # Get the relevant content for each result
    with ThreadPoolExecutor() as executor:
        relevant_content_futures = [executor.submit(get_relevant_content, search_query, result['contents']) for result in best_10_percent]
        done, not_done = wait(relevant_content_futures, timeout=25)
        for future in done:
            result = best_10_percent[relevant_content_futures.index(future)]
            result['relevant_content'] = future.result()
            best_10_percent[relevant_content_futures.index(future)] = result
        for future in not_done:
            best_10_percent[relevant_content_futures.index(future)]['relevant_content'] = ""
            future.cancel()
    '''

    # Get the relevant content for each result
    with ThreadPoolExecutor() as executor:
        relavant_content_futures = [executor.submit(get_relevant_content, search_query, result['contents']) for result in best_10_percent]
        for future in as_completed(relavant_content_futures):
            result = best_10_percent[relavant_content_futures.index(future)]
            result['relevant_content'] = future.result()
            best_10_percent[relavant_content_futures.index(future)] = result
        
    # Remove the results where relevant_content is empty
    best_10_percent = [result for result in best_10_percent if result['relevant_content']]
    print("NUMBER OF RESULTS: " + str(len(best_10_percent)))
    # Update the embedding and similarity
    with ThreadPoolExecutor() as executor:
        embedding_futures = [executor.submit(get_embedding, result['relevant_content']) for result in best_10_percent]
        done, not_done = wait(embedding_futures, timeout=10)
        for future in done:
            result = best_10_percent[embedding_futures.index(future)]
            result['embedding'] = future.result()
            result['similarity'] = cosine_similarity(search_query_embedding, result['embedding'])
            if result['similarity'] < 0.5:
                result['similarity'] = 0
            best_10_percent[embedding_futures.index(future)] = result
        for future in not_done:
            best_10_percent[embedding_futures.index(future)]['similarity'] = 0.1
            future.cancel()
    # Remove the results where similarity is 0
    best_10_percent = [result for result in best_10_percent if result['similarity'] > 0]
    print("NUMBER OF RESULTS: " + str(len(best_10_percent)))
    if len(best_10_percent) == 0:
        #TODO: Handle this case
        return researcher(instruction_index, all_instructions)
    # Sort the results by similarity
    best_10_percent = sorted(best_10_percent, key=lambda x: x['similarity'], reverse=True)
    # Combine the results
    combined_result = combine_results(best_10_percent, search_query, enc)
    return combined_result

'''
if __name__ == "__main__":
    instructions = [{"label": "RESEARCH", "instruction": "proof of pythygorus theorem", "dependencies": [], "response": ""}]
    result = researcher(0, instructions)
    print(result)
'''