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
    time.sleep(wait_seconds + 20)  # +20s pour être sûr que la bougie est bien close


def run_every_15min(task_func):
    last_execution_time = 0
    while True:
        wait_until_next_15min()
        
        # Protection contre les exécutions multiples
        current_time = time.time()
        if current_time - last_execution_time < 60:  # Minimum 60s entre les exécutions
            print(f"[Scheduler] Protection anti-double exécution: attente supplémentaire...")
            time.sleep(60 - (current_time - last_execution_time))
        
        print(f"\n[Scheduler] Nouvelle bougie 15m close à {datetime.datetime.utcnow()} UTC")
        last_execution_time = time.time()
        task_func()

# Exemple d'utilisation :
if __name__ == "__main__":
    def example_task():
        print("C'est ici qu'on lancera la logique de trading ou la récupération des bougies.")
    run_every_15min(example_task) 