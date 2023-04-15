import stripe
from firebase_admin import firestore, db, credentials
import datetime
import firebase_admin
import pytz
import time
import threading


def handle_stripe_event(event):
    email = event['data']['object']['customer_email']
    subscription_id = event['data']['object']['subscription']
    price_id = stripe.Subscription.retrieve(
        subscription_id)['items']['data'][0]['price']['id']
    type = 'free'
    if price_id == 'price_1Mpj0pJ5DHHQ4H2Xf8XNb49O':
        type = 'basic'
    elif price_id == 'price_1MpjQeJ5DHHQ4H2XPWtZNIDd':
        type = 'advanced'
    elif price_id == 'price_1Mpj04J5DHHQ4H2XBSkMseZS':
        type = 'professional'
    start_date = datetime.datetime.now(
        pytz.timezone('America/New_York')).strftime("%Y-%m-%d")
    user = db.collection('users').where('email', '==', email).get()
    print(user)
    for u in user:
        db.collection('users').document(u.id).update({'subscription': {'start_date': start_date, 'type': type, 'chat': 0, 'instruct': 0, 'uploads': 0}})
        print(u.to_dict())
    print('Subscription updated')
    db.collection('events').document(event['id']).update({'type': 'checkout.session.completed.handled'})


def on_snapshot(col_snapshots, changes, read_time):
    print(col_snapshots)
    for doc in col_snapshots:
        print(u'Received document snapshot: {}'.format(doc.id))
        event = doc.to_dict()
        event['id'] = doc.id
        handle_stripe_event(event)


def thread(col_snapshots, changes, read_time):
    print("\n\n")
    print(u'Thread initialized')
    tz_chi = pytz.timezone('America/New_York')
    now = datetime.datetime.now(tz_chi)
    date_time = now.strftime("%Y-%m-%dT%H:%M:%S.%f")
    print("Current Time = ", date_time)
    threads = []
    threads.append(threading.Thread(target=on_snapshot,args=(col_snapshots, changes, read_time)))
    threads[len(threads)-1].start()


stripe.api_key = "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"
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
    'events').where('type', '==', 'checkout.session.completed')
doc_watch = collection_query.on_snapshot(thread)
while True:
    time.sleep(1)
