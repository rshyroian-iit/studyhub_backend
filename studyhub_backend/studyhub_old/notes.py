import firebase_admin
from firebase_admin import credentials, firestore
import time
import threading
import datetime
import pytz
import ai

def notes_response(text, length_coefficient, format):
    print("Text tokens",ai.num_tokens_from_string(text, "gpt2"))
    print("Length Coefficient", length_coefficient)
    response_tokens = int((4096 - ai.num_tokens_from_string(text, "gpt2") - 150) * length_coefficient)
    print("Response tokens: ",response_tokens)
    print(response_tokens)
    if response_tokens > 1000:
        response_tokens = 1000
    if format == "summary":
        system_message = f"You are an AI trained to summarize your given inputs. You always finish your responses within {response_tokens} tokens."
    if format == "bulletpoints":
        system_message = f"For any text you receive, attentively take comprehensive notes, utilizing • bullet points to efficiently structure and arrange the information. You always finish your responses within {response_tokens} tokens."
    system_message = format
    notes = ai.Models.turbo(prompt=text, tokens=response_tokens, system = system_message)
    return notes


def get_notes(document):
    print(document)
    resource_id = document['resource_id']
    user_id = document['user_id']
    page_start = document['page_start'] - 1
    page_end = document['page_end'] - 1
    length_coefficient = document['length_coefficient']
    format = document['format']
    resource_documents = db.collection('users').document(user_id).collection('resources').document(resource_id).collection('documents').get()
    #print(resource_documents)
    pages = []
    for doc in resource_documents:
        doc_dict = doc.to_dict()
        #print(doc_dict)
        pages += doc_dict['parts']
        #print(doc_dict['parts'])
    pages_to_get_notes = []
    for i in range(len(pages)):
        if i >= page_start and i <= page_end:
            print(pages[i])
            pages_to_get_notes.append(pages[i])
    pages_to_get_notes = " ".join(pages_to_get_notes)
    notes = notes_response(pages_to_get_notes, length_coefficient, format)
    return notes

def handle_request(document):
    print('Handling request')
    try: 
        notes = get_notes(document)
        print(notes)
        resource_dict =  db.collection('users').document(document['user_id']).collection('resources').document(document['resource_id']).get().to_dict()
        current_notes = ""
        if 'notes' in resource_dict:
            current_notes = resource_dict['notes']
        #print(current_notes)
        notes = current_notes + "\n\n" + notes
        db.collection('users').document(document['user_id']).collection('resources').document(document['resource_id']).update({
            'notes': notes
        })
        db.collection('notes').document(document['id']).update({
            'status': 'Response Generated'
        })
    except Exception as e:
        print(e)
        resource_dict =  db.collection('users').document(document['user_id']).collection('resources').document(document['resource_id']).get().to_dict()
        current_notes = ""
        if 'notes' in resource_dict:
            current_notes = resource_dict['notes']
        notes = current_notes + "\n\n" + "Error generating summary"
        db.collection('notes').document(str(document['id'])).update({
            'status': 'Error'
        })
    print('Request handled')

def on_snapshot(col_snapshots, changes, read_time):
    print('collection snapshots:', col_snapshots)
    for doc in col_snapshots:
        print('Sending doc snapshot ' + str(doc.id) + ' to handle_request')
        try:
            document = db.collection('notes').document(
                str(doc.id)).get().to_dict()
            document['id'] = doc.id
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
    'notes').where('status', '==', 'pending')
doc_watch = python_notifier_collection_query.on_snapshot(thread)
while True:
    time.sleep(1)