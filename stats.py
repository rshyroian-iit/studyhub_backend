from firebase_admin import credentials, firestore, storage, db
import firebase_admin
import time
import datetime
import pytz

cred = credentials.Certificate(
    "studyhub-93799-firebase-adminsdk-e188e-ee44de40e7.json")
firebase_admin.initialize_app(cred, {
    'storageBucket': 'studyhub-93799.appspot.com'
})
db = firestore.client()
print('Firestore connection initialized')
date = '2023-04-05'
advanced_collection = db.collection('advanced').get()
conversation_collection = db.collection('conversations').get()
user_collection = db.collection('users').get()
users = []
for i in range(len(advanced_collection)):
    dictionary = advanced_collection[i].to_dict()
    if date in dictionary['updated_at']:
        users.append(dictionary['user_id'])

for i in range(len(conversation_collection)):
    dictionary = conversation_collection[i].to_dict()
    if date in dictionary['updatedAt']:
        users.append(dictionary['user_id'])
users = list(set(users))
for i in range(len(user_collection)):
    dictionary = user_collection[i].to_dict()
    try:
        if dictionary['uid'] in users:
            #print(dictionary)
            print('hello')
    except:
        print(dictionary)
#user = db.collection('users').document(user_id).get().to_dict()
#print(user)
    







'''
users_collection = db.collection('users').get()

#k = 100
#end_time = int(time.time())
#start_time = end_time - k * 86400


proper_user_map = {
email: "example@email.com",
googlePhotoUrl: "https://lh3.go",
name: "Example Name",
logins: 100,
subscription: {
    start_date: "2020-12-01",
    type: "free",
    chat: 10,
    instruct: 10,
    uploads: 10
},
popups: {
    pdf: true,  
    chat: true,
    instruct: true,
},
uid: "exampleuid",
}
'''
'''
accounts_with_missing_info = []
new_users_collection = []


for i in range(len(users_collection)):
    dict = users_collection[i].to_dict()
    new_dict = {}
    new_dict['uid'] = users_collection[i].id
    if 'email' in dict:
        new_dict['email'] = dict['email']
    else:
        new_dict['email'] = 'No email'
        if new_dict['uid'] not in accounts_with_missing_info:
            accounts_with_missing_info.append(new_dict['uid'])
    if 'name' in dict:
        new_dict['name'] = dict['name']
    else:
        new_dict['name'] = 'No name'
        if new_dict['uid'] not in accounts_with_missing_info:
            accounts_with_missing_info.append(new_dict['uid'])
    if 'logins' in dict:
        new_dict['logins'] = dict['logins']
    else:
        new_dict['logins'] = 0
        if new_dict['uid'] not in accounts_with_missing_info:
            accounts_with_missing_info.append(new_dict['uid'])
    if 'subscription' in dict and type(dict['subscription']) != bool:
        new_dict['subscription'] = dict['subscription']
    else:
        start_date = datetime.datetime.now(
        pytz.timezone('America/New_York')).strftime("%Y-%m-%d")
        new_dict['subscription'] = {'start_date': start_date, 'type': 'free', 'chat': 0, 'instruct': 0, 'uploads': 0}
        if new_dict['uid'] not in accounts_with_missing_info:
            accounts_with_missing_info.append(new_dict['uid'])
    if 'popups' in dict:
        new_dict['popups'] = dict['popups']
    else:
        new_dict['popups'] = {'pdf': False, 'chat': False, 'instruct': False}
        if new_dict['uid'] not in accounts_with_missing_info:
            accounts_with_missing_info.append(new_dict['uid'])
    if 'googlePhotoUrl' in dict:
        new_dict['googlePhotoUrl'] = dict['googlePhotoUrl']
    else:
        new_dict['googlePhotoUrl'] = 'No googlePhotoUrl'
        if new_dict['uid'] not in accounts_with_missing_info:
            accounts_with_missing_info.append(new_dict['uid'])
    new_users_collection.append(new_dict)
print('New users collection created')
print('Accounts with missing info:', accounts_with_missing_info, len(accounts_with_missing_info))
print('New users collection length:', len(new_users_collection))

#for i in range(len(new_users_collection)):
#    db.collection('users').document(new_users_collection[i]['uid']).set(new_users_collection[i])
    # if a document db.collection('users').document(new_users_collection[i]['uid']) has any collections, delete them
    # if a document db.collection('users').document(new_users_collection[i]['uid']) has any subcollections, delete them

for i in range(len(users_collection)):
    resource_collection = db.collection('users').document(users_collection[i].id).collection('resources').get()
    for j in range(len(resource_collection)):
        db.collection('users').document(users_collection[i].id).collection('resources').document(resource_collection[j].id).delete()
'''