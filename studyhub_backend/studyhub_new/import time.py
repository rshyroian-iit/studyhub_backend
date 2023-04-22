import time
import traceback
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from threading import Timer

# Initialize Firebase
cred = credentials.Certificate("studyhub-93799-firebase-adminsdk-e188e-ee44de40e7.json")
firebase_admin.initialize_app(cred, {
    'storageBucket': 'studyhub-93799.appspot.com'
})
print('Initializing Firestore connection...')
db = firestore.client()
print('Connection initialized')


class Metrics:
    def __init__(self):
        self.performance_events = []
        self.upload_interval = 6
        self.timer = Timer(self.upload_interval, self.upload_performance_metrics)
        self.timer.start()

    def log_error(self, error, stack_trace):
        user_id = 'no_user'  # Replace with actual user id when available
        try:
            db.collection('error_log').add({
                'error_message': str(error),
                'stack_trace': str(stack_trace),
                'timestamp': firestore.SERVER_TIMESTAMP,
                'user_id': user_id,
            })
        except Exception as e:
            print(f'Error logging error: {e}')

    def log_performance_metric(self, metric_name, value):
        user_id = 'no_user'  # Replace with actual user id when available
        if not user_id:
            return

        self.performance_events.append({
            'metric_name': metric_name,
            'value': value,
            'user_id': user_id,
            'timestamp': firestore.SERVER_TIMESTAMP,
        })

    def upload_performance_metrics(self):
        user_id = 'no_user'  # Replace with actual user id when available
        if not user_id:
            return

        try:
            for event in self.performance_events:
                db.collection('performance_metrics').add(event)

            # Clear the performance events list
            self.performance_events.clear()
        except Exception as e:
            error_message = f'Error uploading performance metrics: {e}'
            self.log_error(error_message, traceback.format_exc())

        # Restart the timer
        self.timer = Timer(self.upload_interval, self.upload_performance_metrics)
        self.timer.start()


if __name__ == "__main__":
    metrics = Metrics()
    metrics.log_performance_metric("test_metric", 42)