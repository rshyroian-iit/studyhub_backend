import ocrmypdf
import os
from PyPDF2 import PdfReader, PdfWriter, PdfMerger
from pdfreader import PDFDocument, SimplePDFViewer
from PIL import Image
from wrappers import time_it
import re
import pytesseract
import pdfplumber

@time_it
def ocr_pdf_to_text(file_name):
    try:
        ocrmypdf.ocr(file_name, 'output.pdf', deskew=True, force_ocr=True)
        file_name = 'output.pdf'
        print(file_name)
        reader = PdfReader(open(file_name, 'rb'))
        pages = [page.extract_text() for page in reader.pages]
       # citations = get_citation_from_pdf(pages, file_name)
       # clear all empty pages
        pages = [page for page in pages if len(page) > 100]
        pages = [(f""" --- Begin page {i+1} of {len(pages)+ 1} in {file_name} --- \n
                    {pages[i]} \n
                    --- End page {i+1} of {len(pages)+ 1} in {file_name} --- \n
                    """) for i in range(len(pages))]
        print('Exiting pdf_to_text')
        return pages
    except Exception as e:
        print(e)
        print("An error has occurred while extracting the text from the pdf file. Try another file.")
        return []

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
        print("blia")
        for image in page.images:
            print("HERE")
            try:
                with open(image.name, "wb") as fp:
                    fp.write(image.data)
                    try:
                        img = Image.open(image.name)
                        pdf_reader_text += ' ' + \
                            clean_text(pytesseract.image_to_string(
                                img).replace('|', 'I'))
                    except:
                        pass
                '''
                try:
                    os.remove(image.name)
                except Exception as e:
                    print(e)
                    pass
                '''
            except:
                pass
    except Exception as e:
        print(e)
        pass
    pdf_reader_text
    try:
        pdf_reader_text = pdf_reader_text.encode('utf-8').decode('utf-8')
    except UnicodeDecodeError:
        print('UnicodeDecodeError')
        pdf_reader_text = ''
    return pdf_reader_text

@time_it
def pdf_to_text(file_name):
    try:
        print(file_name)
        print('Entering pdf_to_text')
        reader = PdfReader(open(file_name, 'rb'))
        print('reader created')
        pages = [extract_text_from_page(page) for page in reader.pages]
        print('pages extracted')
       # citations = get_citation_from_pdf(pages, file_name)
       # clear all empty pages
        pages = [page for page in pages]
        print('pages cleared')
        pages = [(f""" --- Begin page {i+1} of {len(pages)+ 1} in {file_name} --- \n
                    {pages[i]} \n
                    --- End page {i+1} of {len(pages)+ 1} in {file_name} --- \n
                    """) for i in range(len(pages))]
        print('Exiting pdf_to_text')
        return pages
    except Exception as e:
        print(e)
        print("An error has occurred while extracting the text from the pdf file. Try another file.")
        return []
'''    
ocr_text = ocr_pdf_to_text('David_M._Burton_Elementary_Number_Theoryz-lib.org_ 2.pdf')
regular_text = pdf_to_text('David_M._Burton_Elementary_Number_Theoryz-lib.org_ 2.pdf')

for i in range(len(ocr_text)):
    if len(ocr_text[i]) < len(regular_text[i]):
        print(ocr_text[i])
        print(regular_text[i])
'''

def test_(file_name):
    pdfPy2Pdf = PdfReader(open(file_name, 'rb'))
    image_pdf = PdfWriter()
    image_dict = {}
    j = 0
    pdfPlumber = pdfplumber.open(file_name)
    for i in range(len(pdfPlumber.pages)):
        print(i)
        if i > 5:
            break
        if pdfPlumber.pages[i].images:
            for image in pdfPlumber.pages[i].images:
                print(image)
                print('name: ', image['name'], '  width: ', image['width'], '  height: ', image['height'], '  page width: ', pdfPlumber.pages[i].width, '  page height: ', pdfPlumber.pages[i].height)
                # save image 
                    
            image_pdf.add_page(pdfPy2Pdf.pages[i])
            image_dict[i] = j
            j += 1
    image_pdf.write('image.pdf')
    image_pdf.close()
    pdfPlumber.close()
    print(image_dict)
    ocrmypdf.ocr('image.pdf', 'image.pdf', deskew=True, force_ocr=True)
    image_pdf = PdfReader(open('image.pdf', 'rb'))
    final_pdf = PdfWriter()
    for i in range(len(pdfPy2Pdf.pages)):
        if i not in image_dict:
            final_pdf.add_page(pdfPy2Pdf.pages[i])
        else:
            final_pdf.add_page(image_pdf.pages[image_dict[i]])
    final_pdf.write('final.pdf')
    final_pdf.close()
    return

    
#test_('David_M._Burton_Elementary_Number_Theoryz-lib.org_ 2.pdf')
        
#regular_text = pdf_to_text('David_M._Burton_Elementary_Number_Theoryz-lib.org_ 2.pdf')
#print(regular_text)
import os

path, file_extension = os.path.splitext('0cKzkdPBXhYFzJs7a6ZF5HZmarf1/Investment Banking (1).pdf.pdf')
print(path)
print(file_extension)