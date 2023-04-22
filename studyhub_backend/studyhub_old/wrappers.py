import time
import threading

def timeout(seconds=10):
    def decorator(func):
        def wrapper(*args, **kwargs):
            result = [None]
            error = [None]

            def target():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    error[0] = e

            thread = threading.Thread(target=target)
            thread.start()
            thread.join(seconds)

            if thread.is_alive():
                # The function is still running after the timeout
                raise TimeoutError("Function timed out")

            if error[0] is not None:
                # The function raised an exception
                raise error[0]

            return result[0]

        return wrapper

    return decorator


def time_it(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        print(f"Entering {func.__name__}")
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"Exiting {func.__name__}")
        print(
            f"Time taken by {func.__name__}: {end_time - start_time:.2f} seconds")
        return result
    return wrapper

