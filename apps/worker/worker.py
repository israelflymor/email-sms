from redis import Redis
from rq import Worker, Queue, Connection
from packages.config.settings import settings

def main():
    redis_conn = Redis.from_url(settings.redis_url)
    with Connection(redis_conn):
        worker = Worker([Queue("outbound_messages")])
        worker.work()

if __name__ == "__main__":
    main()
