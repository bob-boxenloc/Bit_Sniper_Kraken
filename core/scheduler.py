import time
import datetime

def wait_until_next_15min():
    now = datetime.datetime.utcnow()
    # Prochaine minute multiple de 15
    next_minute = (now.minute // 15 + 1) * 15
    if next_minute == 60:
        next_hour = now.replace(minute=0, second=0, microsecond=0) + datetime.timedelta(hours=1)
        next_candle = next_hour
    else:
        next_candle = now.replace(minute=next_minute, second=0, microsecond=0)
    wait_seconds = (next_candle - now).total_seconds()
    print(f"Attente jusqu'à la prochaine clôture de bougie 15m : {next_candle} UTC ({int(wait_seconds)}s)")
    time.sleep(wait_seconds + 2)  # +2s pour être sûr que la bougie est bien close


def run_every_15min(task_func):
    while True:
        wait_until_next_15min()
        print(f"\n[Scheduler] Nouvelle bougie 15m close à {datetime.datetime.utcnow()} UTC")
        task_func()

# Exemple d'utilisation :
if __name__ == "__main__":
    def example_task():
        print("C'est ici qu'on lancera la logique de trading ou la récupération des bougies.")
    run_every_15min(example_task) 