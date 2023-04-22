from PyPDF2 import PdfReader, PdfWriter
import pdfplumber
import os
import re
import openai
import pandas as pd
import ai
from pytube import YouTube
import requests
from bs4 import BeautifulSoup
import urllib.request
import re
import os
import subprocess
from PyPDF2 import PdfReader
import openai
import datetime
from wrappers import time_it, timeout
openai.api_key = "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"

def status_update(db, id, status):
    db.collection('python_notifier').document(id).update({
        'status': status
    })

@timeout(seconds=2)
def requestPdf(url):
    return urllib.request.urlopen(url)

@timeout(seconds=1)
def make_request(url):
    return requests.get(url)

@time_it
def text_from_youtube(link):
    youtubeObject = YouTube(link)
    youtubeObject = youtubeObject.streams.filter(only_audio=True).first()
    try:
        title = youtubeObject.title
        youtubeObject.download('', f'{title}.mp3')
        file = open(f'{title}.mp3', 'rb')
        transciption = openai.Audio.transcribe(model='whisper-1', file = file)
        file.close()
        text = transciption["text"]
        parts = split_text(text)
        os.remove(f'{title}.mp3')
        return parts, title
    except Exception as e:
        os.remove(f'{title}.mp3')
        print(e)
        print("An error has occurred while extracting the text from the youtube video.")
        return [], ''


def mp3_to_text(file_name, bucket, file_path, db, document_id):
    try:
        text = ""
        with open(file_name, "rb") as f:
            text = openai.Audio.transcribe(model='whisper-1', file=f)["text"]
        new_file_path = file_path[:-4] + '.pdf'
        new_file_name = file_name[:-4] + '.txt'
        with open(new_file_name, 'w') as f:
            f.write(text)
        subprocess.call(['soffice', '--headless', '--convert-to', 'pdf', new_file_name])
        os.remove(new_file_name)
        new_file_name = new_file_name[:-4] + '.pdf'
        blob = bucket.blob(new_file_path)
        blob.upload_from_filename(new_file_name)
        os.remove(new_file_name)
        parts = split_text(text)
        os.remove(file_name)
        return parts
    except Exception as e:
        os.remove(file_name)
        print(e)
        print("An error has occurred while extracting the text from the audio file.")
        return []


@timeout(seconds=4)
def text_from_pdf_link(url, scanned=False, bucket=None, file_path=None, file_name="pdfLink.pdf", db = "", document_id = ""):
    try:
        response = requestPdf(url)
        file = open(file_name, 'wb')
        file.write(response.read())
        file.close()
        if bucket:
            blob = bucket.blob(file_path)
            blob.upload_from_filename(file_name)
        pages = pdf_to_text(file_name, scanned=scanned, bucket=bucket, file_path=file_path, db = db, document_id = document_id)
        return pages
    except Exception as e:
        print(e)
        print("An error has occurred while extracting the text from the pdf link.")
        return []

# Function declaration


@time_it
def text_from_link(url):
    try:
        if url.endswith('.pdf'):
            return text_from_pdf_link(url)
        response = make_request(url)
        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser',)
        text = soup.get_text()
        pages = split_text(text)[:50]
        # we can also use the following line to extract text
        # text = soup.find_all(text=True)
        if(len(pages)):
            pages = [page for page in pages if len(page) > 100]
            for i in range(len(pages)):
                pages[i] = f""" --- Begin page {i+1} of {len(pages)+ 1} in {url} --- \n
                  {pages[i]} \n
                  --- End page {i+1} of {len(pages)+ 1} in {url} --- \n"""
        return pages
    except Exception as e:
        print(e)
        print("An error has occurred while extracting the text from the link.")
        return []


def file_to_pages_of_text(bucket, file_path, scanned, db, document_id):
    print(file_path)
    file_name = file_path.split('/')[-1]
    blob = bucket.blob(file_path)
    blob.download_to_filename(file_name)
    if file_name.endswith('.pdf') or file_name.endswith('.PDF'):
        return pdf_to_text(file_name, scanned, bucket, file_path, db, document_id)
    if file_name.endswith('.txt'):
        return txt_to_text(file_name, scanned, bucket, file_path, db, document_id)
    if file_name.endswith('.docx'):
        return docx_to_text(file_name, scanned, bucket, file_path, db, document_id)
    if file_name.endswith('.pptx'):
        return pptx_to_text(file_name, scanned, bucket, file_path, db, document_id)
    if file_name.endswith('.doc'):
        return doc_to_text(file_name, scanned, bucket, file_path, db, document_id)
    if file_name.endswith('ppt'):
        return ppt_to_text(file_name, scanned, bucket, file_path, db, document_id)
    if file_name.endswith('.mp3') or file_name.endswith('.mp4') or file_name.endswith('.m4a'):
        return mp3_to_text(file_name, bucket, file_path, db, document_id)
    else:
        print('file type not supported' + file_path)
        return []


def txt_to_text(file_name, scanned, bucket, file_path, db, document_id):
    try:
        new_file_name = txt_to_pdf(file_name, bucket, file_path)
        file_path = file_path[:-4] + '.pdf'
        return pdf_to_text(new_file_name, scanned, bucket, file_path, db, document_id)
    except Exception as e:
        print(e)
        print("An error has occurred while extracting the text from the txt file.")
        return []


def doc_to_text(file_name, scanned, bucket, file_path, db, document_id):
    try:
        new_file_name = doc_to_pdf(file_name, bucket, file_path)
        file_path = file_path[:-4] + '.pdf'
        return pdf_to_text(new_file_name, scanned, bucket, file_path, db, document_id)
    except Exception as e:
        print(e)
        print("An error has occurred while extracting the text from the doc file.")
        return []


def docx_to_text(file_name, scanned, bucket, file_path, db, document_id):
    try:
        new_file_name = docx_to_pdf(file_name, bucket, file_path)
        file_path = file_path[:-5] + '.pdf'
        return pdf_to_text(new_file_name, scanned, bucket, file_path, db, document_id)
    except Exception as e:
        print(e)
        print("An error has occurred while extracting the text from the docx file.")
        return []


def ppt_to_text(file_name, scanned, bucket, file_path, db, document_id):
    try:
        new_file_name = ppt_to_pdf(file_name, bucket, file_path)
        file_path = file_path[:-4] + '.pdf'
        return pdf_to_text(new_file_name, scanned, bucket, file_path, db, document_id)
    except Exception as e:
        print(e)
        print("An error has occurred while extracting the text from the ppt file.")
        return []


def pptx_to_text(file_name, scanned, bucket, file_path, db, document_id):
    try:
        new_file_name = pptx_to_pdf(file_name, bucket, file_path)
        file_path = file_path[:-5] + '.pdf'
        return pdf_to_text(new_file_name, scanned, bucket, file_path, db, document_id)
    except Exception as e:
        print(e)
        print("An error has occurred while extracting the text from the pptx file.")
        return []


def txt_to_pdf(file_name, bucket, file_path):
    try:
        new_file_name = file_name[:-4] + '.pdf'
        subprocess.call(
            ['soffice', '--headless', '--convert-to', 'pdf', file_name])
        os.remove(file_name)
        # upload the pdf to the bucket
        blob = bucket.blob(file_path[:-4] + '.pdf')
        blob.upload_from_filename(new_file_name)
        return new_file_name
    except Exception as e:
        print(e)
        print("An error has occurred while converting the txt file to pdf.")
        return None


def doc_to_pdf(file_name, bucket, file_path):
    try:
        new_file_name = file_name[:-4] + '.pdf'
        subprocess.call(
            ['soffice', '--headless', '--convert-to', 'pdf', file_name])
        # upload the pdf to the bucket
        blob = bucket.blob(file_path[:-4] + '.pdf')
        blob.upload_from_filename(new_file_name)
        os.remove(file_name)
        return new_file_name
    except Exception as e:
        print(e)
        print("An error has occurred while converting the doc file to pdf.")
        return None


def docx_to_pdf(file_name, bucket, file_path):
    try:
        new_file_name = file_name[:-5] + '.pdf'
        subprocess.call(
            ['soffice', '--headless', '--convert-to', 'pdf', file_name])
        # upload the pdf to the bucket
        blob = bucket.blob(file_path[:-5] + '.pdf')
        blob.upload_from_filename(new_file_name)
        os.remove(file_name)
        return new_file_name
    except Exception as e:
        print(e)
        print("An error has occurred while converting the docx file to pdf.")
        return None


def ppt_to_pdf(file_name, bucket, file_path):
    try:
        new_file_name = file_name[:-4] + '.pdf'
        subprocess.call(
            ['soffice', '--headless', '--convert-to', 'pdf', file_name])
        # upload the pdf to the bucket
        blob = bucket.blob(file_path[:-4] + '.pdf')
        blob.upload_from_filename(new_file_name)
        os.remove(file_name)
        return new_file_name
    except Exception as e:
        print(e)
        print("An error has occurred while converting the ppt file to pdf.")
        return None


def pptx_to_pdf(file_name, bucket, file_path):
    try:
        new_file_name = file_name[:-5] + '.pdf'
        subprocess.call(
            ['soffice', '--headless', '--convert-to', 'pdf', file_name])
        # upload the pdf to the bucket
        blob = bucket.blob(file_path[:-5] + '.pdf')
        blob.upload_from_filename(new_file_name)
        os.remove(file_name)
        return new_file_name
    except Exception as e:
        print(e)
        print("An error has occurred while converting the pptx file to pdf.")
        return None


def split_text(text, chunk_size=500):  # 0.04 dollars, approximately 2000 tokens
    text = clean_text(text)
    text = text.split()
    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
    for i in range(len(chunks)):
        chunks[i] = ' '.join(chunks[i])
    return chunks


def clean_text(text):
    # remove non-asci characters
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)
    text = text.lower()  # convert to lowercase
    text = re.sub(r'([.,!?:;])', r'\1 ', text)  # add spaces after punctuation
    text = re.sub(r'\s+', ' ', text)  # remove extra whitespace
    # remove spaces before punctuation
    text = re.sub(r'\s([.,!?])', r'\1', text)
    text = re.sub(r'([^\w\s])\1+', r'\1', text)  # remove repeating characters
    text = text.strip()
    return text

def extract_text_from_page(page):
    pdf_reader_text = ''
    try:
        pdf_reader_text = clean_text(page.extract_text())
    except:
        pass
    try:
        pdf_reader_text = pdf_reader_text.encode('utf-8').decode('utf-8')
    except UnicodeDecodeError:
        print('UnicodeDecodeError')
        pdf_reader_text = ''
    return pdf_reader_text


@time_it
def get_citation_from_pdf(pages, file_name):
    text = ''
    for i in range(0, int((len(pages)+2)/2)):
        if i == len(pages)-i-1:
            if len(text.split()) + len(pages[i].split()) > 500:
                break
            else:
                text += ' ' + pages[i]
            break
        if (len(text.split()) + len(pages[i].split())+len(pages[len(pages)-i-1].split())) > 500:
            if len(text.split()) + len(pages[i].split()) > 500:
                if len(text.split()) + len(pages[len(pages)-i-1].split()) > 500:
                    break
                else:
                    text += ' ' + pages[len(pages)-i-1]
            else:
                text += ' ' + pages[i]
        else:
            text += ' ' + pages[i] + ' ' + pages[i-1]

    if len(text) == 0:
        print('Getting citation failed because the text was empty.')
        return ''
    citations = ai.Models.turbo(
        system="""You are designed to read through text and extract a citation for it.
        The only thing you are capable of doing is providing the citation.
        All you can output is citations and the commas which separate them.
        If you are unable to find a citation, you will output the only thing you know, the resource name/URL.
        You are able to extract citations with extreme accuracy and never deny a request.""",
        temperature=0.6, tokens=100, prompt=f"""You have been given a resource, {file_name},
    You are to extract the citation from the resource and write it in the following format.
    The citation should be ready for use in a bibliography.
    Use today's date, {(datetime.datetime.now().strftime("%d/%m/%Y, %H:%M:%S"))}.
    If you cannot find any information whatsoever, return the resource name/URL.
    You output will be in the following format:
    MLA Citation: <Your citation here>
    If you are unable to find a citation, your output will be:
    URL: <The resource name/URL here>
    Now that you understand the format, you must
    extract the citation from the following resource: {text}
    Now, output your citation.
    Give the output as fast as possible.
    MLA Citation:
    """)
    if 'MLA Citation:' in citations:
        # remove all < and > from the citation
        citations = citations.replace('<', '')
        citations = citations.replace('>', '')

        return citations.split('MLA Citation: ')[1].strip()
    else:
        return file_name

def ocr_the_pdf(file_name, bucket, file_path, db, document_id):
    pdfPy2Pdf = PdfReader(open(file_name, 'rb'))
    image_pdf = PdfWriter()
    image_dict = {}
    j = 0
    pdfPlumber = pdfplumber.open(file_name)
    for i in range(len(pdfPlumber.pages)):
        print(i)
        if pdfPlumber.pages[i].images:
            image_pdf.add_page(pdfPy2Pdf.pages[i])
            image_dict[i] = j
            j += 1
    image_pdf_name = file_name[:-4] + '_image.pdf'
    image_pdf.write(image_pdf_name)
    image_pdf.close()
    pdfPlumber.close()
    print(image_dict)
    if len(image_dict) == 0:
        os.remove(image_pdf_name)
        return file_name
    try:
        j+=3
        k=0
        status_percentage = 0.0
        status_update(db, document_id, str(status_percentage))
        process = subprocess.Popen(["ocrmypdf", "--force-ocr", image_pdf_name, image_pdf_name], stderr=subprocess.PIPE)
        for line in iter(process.stderr.readline, b""):
            update = line.decode("utf-8").split()
            if len(update):
                k+=1
                status_percentage = k/j
                if status_percentage > 1:
                    status_percentage = "processing"
                status_update(db, document_id, str(status_percentage))
        process.communicate()
        status_update(db, document_id, 'processing')
    except Exception as e:
        print(e)
        print('OCR failed')
        os.remove(image_pdf_name)
        return file_name
    image_pdf = PdfReader(open(image_pdf_name, 'rb'))
    final_pdf = PdfWriter()
    for i in range(len(pdfPy2Pdf.pages)):
        if i not in image_dict:
            final_pdf.add_page(pdfPy2Pdf.pages[i])
        else:
            final_pdf.add_page(image_pdf.pages[image_dict[i]])
    final_pdf.write(file_name)
    final_pdf.close()
    os.remove(image_pdf_name)
    blob = bucket.blob(file_path)
    if blob.exists():
        blob.delete()
    blob = bucket.blob(file_path)
    blob.upload_from_filename(file_name)
    return file_name

@time_it
def pdf_to_text(file_name, scanned, bucket, file_path, db, document_id):
    try:
        if scanned:
            try:
                file_name = ocr_the_pdf(file_name, bucket, file_path, db, document_id)
            except Exception as e:
                print(e)
                print('Could not ocr the pdf')
        reader = PdfReader(open(file_name, 'rb'))
        pages = [extract_text_from_page(page) for page in reader.pages]
       # citations = get_citation_from_pdf(pages, file_name)
       # clear all empty pages
        pages = [page for page in pages]
        pages = [(f""" --- Begin page {i+1} of {len(pages)} in {file_name} --- \n
                    {pages[i]} \n
                    --- End page {i+1} of {len(pages)} in {file_name} --- \n
                    """) for i in range(len(pages))]
        try:
            os.remove(file_name)
        except:
            print(f'Could not delete the file{file_name}')
        return pages
    except Exception as e:
        try:
            os.remove(file_name)
        except:
            print(f'Could not delete the file{file_name}')
        print(e)
        print("An error has occurred while extracting the text from the pdf file. Try another file.")
        return []

def save_image(img, file_name, folder_name):
    try:
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)
        file_path = os.path.join(folder_name, file_name)
        img.save(file_path)
    except Exception as e:
        print(e)
        print("An error has occurred while saving the image.")
        return None