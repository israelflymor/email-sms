import time
from packages.config.settings import settings
from packages.db.session import SessionLocal
from packages.services.scheduler import run_scheduler_tick

def main():
    while True:
        db = SessionLocal()
        try:
            run_scheduler_tick(db)
        finally:
            db.close()
        time.sleep(max(settings.campaign_batch_interval_seconds, 5))

if __name__ == "__main__":
    main()
