import threading
from multiprocessing import Process
import time
import queue

"""
    Examples with multithreading and multiprocessing

"""


def cpu_bound_task():
    count = 0
    for i in range(10**7):
        count += 1


def thd1_task():
    for i in range(5):
        print(f"Thread 1 - Hello from the thread.")
        time.sleep(0.2)


def thd2_task(name, count):
    for i in range(count):
        print(f"{name} - says: {i}.")
        time.sleep(0.5)


def infinity_thread():
    while True:
        print("                               daemon still running...")
        time.sleep(3)


def producer(queue):
    for i in range(8):
        item = f"item-{i}"
        print(f" Producing {item} -->>")
        queue.put(item)
        time.sleep(0.2)
    queue.put(None)     # Signal to consumer that production is empty


def consumer(queue):
    while True:
        item = queue.get()
        if item is None:
            break
        print(f" -->> Consuming {item}")
        time.sleep(0.5)


def worker(event):
    print(f"Worker waiting for event to start.")
    event.wait()        # wait until the event is set
    print(f"Worker starting work.")
    for i in range(5):
        print(f"Working...")
        time.sleep(0.3)
    print(f"Worker finished.")


def main():

    print(f"----------  1.   -----------")
    # 1. simple thread with join
    th1 = threading.Thread(target=thd1_task)
    th1_name = th1.name
    th1.start()
    print(f"Main - ({th1_name}) started.")
    th1.join()
    print(f"Main - ({th1_name}) finished.")

    print(f"----------  2.   -----------")
    # 2. thread delayed with arguments
    th2 = threading.Timer(3, thd2_task, args=("Asterisk", 5))
    th2_name = th2.name
    th2.start()
    print(f"Main - ({th2_name}) started.")
    th2.join()
    print(f"Main - ({th2_name}) finished.")

    print(f"----------  3.   -----------")
    # 3. daemon
    daemon_thread = threading.Thread(target=infinity_thread)
    daemon_thread.daemon = True
    dmon_name = daemon_thread.name
    daemon_thread.start()
    print(f"Daemon thread ({dmon_name}) started.")

    print(f"----------  4.   -----------")
    # queue
    q = queue.Queue()
    producer_thd = threading.Thread(target=producer, args=(q,))
    consumer_thd = threading.Thread(target=consumer, args=(q,))
    prod_name = producer_thd.name
    cons_name = consumer_thd.name
    producer_thd.start()
    consumer_thd.start()
    print(f"Main - (producer={prod_name}, consumer={cons_name}) started.")
    producer_thd.join()
    consumer_thd.join()
    print(f"Main - (producer={prod_name}, consumer={cons_name}) finished.")

    print(f"----------  5.   -----------")
    # threading event
    event = threading.Event()
    # thread prepared but with event.wait()
    th_worker = threading.Thread(target=worker, args=(event,))
    thw_name = th_worker.name
    print(f"Main - ({thw_name}) prepared to start.")
    th_worker.start()
    time.sleep(2)
    print(f"Main - ({thw_name}) set the event.")
    event.set()         # Start the worker Thread
    th_worker.join()
    print(f"Main - ({thw_name}) finished.")

    print(f"----------  6.   -----------")
    # multiprocessing
    print(f"Compare multithreading and multiprocessing.")
    time_start = time.time()
    threads = [threading.Thread(target=cpu_bound_task) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    print(
        f"Elapsed time with multithreading: {time.time() - time_start:.3f} seconds")

    time_start = time.time()
    processes = [Process(target=cpu_bound_task) for _ in range(4)]

    for process in processes:
        process.start()

    for process in processes:
        process.join()

    print(
        f"Elapsed time with multiprocessing: {time.time() - time_start:.3f} seconds")


if __name__ == "__main__":
    main()
