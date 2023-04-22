import ai
import time
from firebase_admin import credentials, firestore, storage, db
import firebase_admin
from resources import file_to_pages_of_text, split_text, text_from_link, text_from_pdf_link, text_from_youtube
import threading
import time
import openai
import datetime
import pytz
import os
import subprocess
import validators
openai.api_key = "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"

def name_a_url(url):
    response = openai.ChatCompletion.create(model = "gpt-3.5-turbo", max_tokens = 15, messages = [{'role': 'assistant', 'content': f"Give a good name to this URL: {url} within 10 tokens."}])
    name = response['choices'][0]['message']['content']
    return name

def extract_text_to_db(document):
    user_id = document['userId']
    resource_id = document['resourceId']
    db.collection('python_notifier').document(
        str(document['id'])).update({'status': 'processing'})
    resource = db.collection('users').document(
        user_id).collection('resources').document(resource_id).get().to_dict()
    if 'job' in document:
        if document['job'] == 'updateUrl':
            pdf_url = storage.bucket().blob(resource['path']).generate_signed_url(
                expiration=datetime.timedelta(days=1), version='v4', response_type='application/pdf')
            db.collection('users').document(user_id).collection('resources').document(resource_id).update({
                'pdfUrl': pdf_url
            })
            db.collection('python_notifier').document(
                str(document['id'])).update({'pdfUrl': pdf_url, 'status': 'complete'})
            return
    user_subscription = db.collection('users').document(user_id).get().to_dict()['subscription']
    chat_limit = 0
    instruct_limit = 0
    uploads_limit = 0
    if user_subscription['type'] == 'free':
        chat_limit = 10
        instruct_limit = 2
        uploads_limit = 2
    if user_subscription['type'] == 'basic':
        chat_limit = 200
        instruct_limit = 10
        uploads_limit = 10
    if user_subscription['type'] == 'advanced':
        chat_limit = 100000
        instruct_limit = 25
        uploads_limit = 50
    if user_subscription['type'] == 'professional':
        chat_limit = 100000
        instruct_limit = 100000
        uploads_limit = 100000
    if user_subscription['uploads'] >= uploads_limit:
        db.collection('python_notifier').document(
            str(document['id'])).update({'status': 'limit_reached'})
        return
    upload_type = resource['uploadType']
    scanned = False
    if 'scanned' in resource:
        scanned = resource['scanned']
    if(upload_type == 'file'):
        path = resource['path']
        pages = file_to_pages_of_text(bucket, path, scanned, db, document['id'])
        path, file_extension = os.path.splitext(path)
        path += '.pdf'
        pdf_url = storage.bucket().blob(path).generate_signed_url(
            expiration=datetime.timedelta(days=1), version='v4', response_type='application/pdf')
        num_documents = len(pages)//20 + 1
        num_words = sum([len(page.split()) for page in pages])
        if num_words == 0:
            db.collection('python_notifier').document(
                str(document['id'])).update({'status': 'error'})
            return
        db.collection('users').document(user_id).collection('resources').document(resource_id).update({
            'wordCount': num_words,
            'path': path,
            'pages': len(pages),
            'pdfUrl': pdf_url
        })
        for i in range(num_documents):
            if i == num_documents-1:
                p = pages[i*20:]
            else:
                p = pages[i*20:(i+1)*20]
            embeddings = ai.Models.get_list_of_embeddings(p)
            db.collection('users').document(
                user_id).collection('resources').document(resource_id).collection('documents').document(str(i)).set({
                    'parts': p, 'embeddings': embeddings
                })
        user_subscription['uploads'] += 1
        db.collection('users').document(user_id).update({'subscription': user_subscription})
            
    if(upload_type == 'text'):
        if validators.url(resource['text'].strip()):
            if 'www.youtube.com' in resource['text']:
                upload_type = 'youtube'
            else:
                upload_type = 'link'
        else:
            name = ai.give_a_name(text=resource['text'], reader=True)
            parts = split_text(resource['text'])
            num_documents = len(parts)//20 + 1
            num_words = sum([len(part.split()) for part in parts])
            file_name = name + '.txt'
            path_name = user_id + '/' + name + '.pdf'
            with open(file_name, 'w') as f:
                f.write(resource['text'])
            subprocess.call(['soffice', '--headless', '--convert-to', 'pdf', file_name])
            os.remove(file_name)
            file_name = file_name[:-4] + '.pdf'
            blob = bucket.blob(path_name)
            blob.upload_from_filename(file_name)
            os.remove(file_name)
            pdf_url = storage.bucket().blob(path_name).generate_signed_url(
                expiration=datetime.timedelta(days=1), version='v4', response_type='application/pdf')
            pdf_link = f'<a href="{pdf_url}">Download PDF</a>'
            db.collection('users').document(user_id).collection('resources').document(resource_id).update({
                'wordCount': num_words,
                'pages': len(parts),
                'nickName': name,
                'path': path_name,
                'pdfUrl': pdf_url
            })
            for i in range(num_documents):
                if i == num_documents-1:
                    p = parts[i*20:]
                else:
                    p = parts[i*20:(i+1)*20]
                embeddings = ai.Models.get_list_of_embeddings(p)
                db.collection('users').document(
                    user_id).collection('resources').document(resource_id).collection('documents').document(str(i)).set({
                        'parts': p, 'embeddings': embeddings
                    })
            user_subscription['uploads'] += 1
            db.collection('users').document(user_id).update({'subscription': user_subscription})
            
    if(upload_type == 'link'):
        '''new_file_name = file_name[:-4] + '.pdf'
        subprocess.call(
            ['soffice', '--headless', '--convert-to', 'pdf', file_name])
        os.remove(file_name)
        # upload the pdf to the bucket
        blob = bucket.blob(file_path[:-4] + '.pdf')
        blob.upload_from_filename(new_file_name)
        return new_file_name'''
        url = str(resource['text']).strip()
        parts = []
        name = name_a_url(url)
        new_path = user_id + '/' + name
        if url.endswith('.pdf'):
            parts = text_from_pdf_link(url, scanned, bucket, new_path, name, db, document['id'])
        else:
            parts = text_from_link(url)
            text = ' '.join(parts)
            name = name + '.txt'
            with open(name, 'w') as f:
                f.write(text)
            subprocess.call(
                ['soffice', '--headless', '--convert-to', 'pdf', name])
            os.remove(name)
            name = name[:-4] + '.pdf'
            new_path = new_path + '.pdf'
            blob = bucket.blob(new_path)
            blob.upload_from_filename(name)
            os.remove(name)
        pdf_url = storage.bucket().blob(new_path).generate_signed_url(
            expiration=datetime.timedelta(days=1), version='v4', response_type='application/pdf')
        pdf_link = f'<a href="{pdf_url}">Download PDF</a>'
        num_documents = len(parts)//20 + 1
        num_words = sum([len(part.split()) for part in parts])
        db.collection('users').document(user_id).collection('resources').document(resource_id).update({
            'wordCount': num_words,
            'pages': len(parts),
            'path': new_path,
            'nickName': name,
            'pdfUrl': pdf_url
        })
        for i in range(num_documents):
            if i == num_documents-1:
                p = parts[i*20:]
            else:
                p = parts[i*20:(i+1)*20]
            embeddings = ai.Models.get_list_of_embeddings(p)
            db.collection('users').document(
                user_id).collection('resources').document(resource_id).collection('documents').document(str(i)).set({
                    'parts': p, 'embeddings': embeddings
                })
        user_subscription['uploads'] += 1
        db.collection('users').document(user_id).update({'subscription': user_subscription})

    elif(upload_type == 'youtube'):
        link = str(resource['text']).strip()
        parts, title = text_from_youtube(link)
        name = title + '.txt'
        new_path = user_id + '/' + name
        youtube_text = ' '.join(parts)
        with open(name, 'w') as f:
            f.write(youtube_text)
        subprocess.call(['soffice', '--headless', '--convert-to', 'pdf', name])
        os.remove(name)
        name = name[:-4] + '.pdf'
        new_path = new_path + '.pdf'
        blob = bucket.blob(new_path)
        blob.upload_from_filename(name)
        os.remove(name)
        num_documents = len([parts])//20 + 1
        num_words = sum([len(part.split()) for part in parts])
        pdf_url = storage.bucket().blob(new_path).generate_signed_url(
            expiration=datetime.timedelta(days=1), version='v4', response_type='application/pdf')
        pdf_link = f'<a href="{pdf_url}">Download PDF</a>'
        db.collection('users').document(user_id).collection('resources').document(resource_id).update({
            'wordCount': num_words,
            'pages': len(parts),
            'path': new_path,
            'nickName': name,
            'pdfUrl': pdf_url
        })
        for i in range(num_documents):
            if i == num_documents-1:
                p = parts[i*20:]
            else:
                p = parts[i*20:(i+1)*20]
            embeddings = ai.Models.get_list_of_embeddings(p)
            db.collection('users').document(
                user_id).collection('resources').document(resource_id).collection('documents').document(str(i)).set({
                    'parts': p, 'embeddings': embeddings
                })
        user_subscription['uploads'] += 1
        db.collection('users').document(user_id).update({'subscription': user_subscription})
    db.collection('python_notifier').document(
        str(document['id'])).update({'status': 'complete'})

def change_status(listener_id, status):
    epoch_time = int(time.time())
    db.collection('python_notifier').document(
        str(listener_id)).update({'status': status, 'end': epoch_time})


def on_snapshot(col_snapshot, changes, read_time):
    print(u'Callback received query snapshot.')
    for doc in col_snapshot:
        print('handling request from ' + doc.id)
        try:
            document = db.collection('python_notifier').document(
                str(doc.id)).get().to_dict()
            print('User id:', document['userId'])
            if document['userId'] == '5yicbnXaxQMCD2iY0WRC8zmPNp13':
                document['id'] = doc.id
                change_status(document['id'], 'processing')
                extract_text_to_db(document)
        except Exception as e:
            print(e)
            change_status(document['id'], 'error')
    return


def thread(col_snapshots, changes, read_time):
    print("\n\n")
    print(u'Thread initialized')
    tz_chi = pytz.timezone('America/Chicago')
    now = datetime.datetime.now(tz_chi)
    current_time = now.strftime("%H:%M:%S")
    print("Current Time =", current_time)
    threads.append(threading.Thread(target=on_snapshot,
                                    args=(col_snapshots, changes, read_time)))
    threads[len(threads)-1].start()


# Firebase connection
cred = credentials.Certificate(
    "studyhub-93799-firebase-adminsdk-e188e-ee44de40e7.json")
firebase_admin.initialize_app(cred, {
    'storageBucket': 'studyhub-93799.appspot.com'
})
bucket = storage.bucket()
print(bucket.list_blobs())
print('Initializing Firestore connection...')
db = firestore.client()
print('Connection initialized')
threads = []
python_notifier_collection_query = db.collection(
    'python_notifier').where('status', '==', 'pending')
doc_watch = python_notifier_collection_query.on_snapshot(thread)
while True:
    time.sleep(1)