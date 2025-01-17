import json
import time
import requests
import random
import csv
from pathlib import Path
from colorama import Fore, Style, init

# Инициализация colorama
init(autoreset=True)

# Функция для логирования
def log_message_csv(data, log_file="log.csv"):
    log_exists = Path(log_file).exists()
    with open(log_file, "a", encoding="utf-8", newline="") as log:
        writer = csv.writer(log)
        if not log_exists:
            writer.writerow(["Время", "Название аккаунта", "Токен", "Прокси", "Сообщение", "Результат"])
        writer.writerow(data)

# Загрузка конфигурации
def load_config(config_path="config.json"):
    with open(config_path, "r", encoding="utf-8") as file:
        return json.load(file)

# Чтение аккаунтов из файла
def load_accounts(file_path, separator=":"):
    accounts = []
    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            parts = line.strip().split(separator)
            if len(parts) >= 4:
                name, token, proxy, variable_message = parts[0], parts[1], parts[2], separator.join(parts[3:])
                accounts.append({"name": name, "token": token, "proxy": proxy, "variable_message": variable_message})
    return accounts

# Отправка сообщения в Discord
def send_message(token, channel_id, message, proxy=None):
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    headers = {
        "Authorization": token,
        "Content-Type": "application/json"
    }
    data = {
        "content": message
    }
    proxies = {
        "http": f"http://{proxy}",
        "https": f"http://{proxy}"
    } if proxy else None

    try:
        response = requests.post(url, headers=headers, json=data, proxies=proxies, timeout=10)
        if response.status_code == 200:
            return True, "Сообщение отправлено успешно", None
        elif response.status_code == 429:
            retry_after_seconds = response.json().get("retry_after", 0)
            hours, remainder = divmod(retry_after_seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            retry_time = f"{int(hours)} часов, {int(minutes)} минут"
            return False, f"Уже запрашивали. Повторный запрос токенов возможен через {retry_time}", retry_after_seconds
        else:
            return False, f"Ошибка {response.status_code}: {response.text}", None
    except Exception as e:
        return False, f"Исключение: {str(e)}", None

# Парсинг диапазона задержки
def parse_delay_range(delay_range_str):
    try:
        min_delay, max_delay = map(int, delay_range_str.split("-"))
        return min_delay, max_delay
    except ValueError:
        raise ValueError("Некорректный формат диапазона задержки. Ожидается формат 'min-max'.")

# Парсинг времени паузы между циклами
def parse_restart_time(restart_time):
    if not restart_time or str(restart_time).lower() == "0":
        return None  # Отключить паузу
    try:
        if restart_time.endswith("h"):
            return int(restart_time[:-1]) * 3600  # Часы в секунды
        elif restart_time.endswith("m"):
            return int(restart_time[:-1]) * 60  # Минуты в секунды
        elif restart_time.endswith("s"):
            return int(restart_time[:-1])  # Уже в секундах
        else:
            raise ValueError("Некорректный формат времени для паузы. Используйте 'h', 'm' или 's'.")
    except ValueError as e:
        raise ValueError(f"Ошибка парсинга времени для паузы: {e}")

# Основной процесс
def main():
    config = load_config()
    channel_id = config["channel_id"]
    separator = config["accounts_separator"]
    delay_range = config["delay_between_messages"]
    constant_message_part = config["constant_message_part"]
    shuffle_accounts = config.get("shuffle_accounts", False)
    restart_time = config.get("restart_after_hours", "0")

    # Разбираем время паузы между циклами
    pause_between_cycles = parse_restart_time(restart_time)

    # Разбираем диапазон задержки
    min_delay, max_delay = parse_delay_range(delay_range)

    while True:
        accounts = load_accounts("accounts.txt", separator)

        # Перемешиваем аккаунты, если включена опция shuffle_accounts
        if shuffle_accounts:
            random.shuffle(accounts)

        print(Fore.GREEN + f"[{time.strftime('%H:%M:%S')}] === Начало отправки сообщений ===")

        for account in accounts:
            name, token, proxy, variable_message = account["name"], account["token"], account["proxy"], account["variable_message"]
            # Формируем сообщение
            full_message = f"{constant_message_part} {variable_message}"
            success, response_message, retry_after_seconds = send_message(token, channel_id, full_message, proxy)

            # Логирование
            time_now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            log_message_csv([time_now, name, token[:10], proxy, full_message, response_message])
            if success:
                print(Fore.CYAN + f"[{time.strftime('%H:%M:%S')}] Аккаунт: {name} | Токен: {token[:10]} | Прокси: {proxy} | Сообщение отправлено: {full_message}")
            else:
                if retry_after_seconds:
                    print(Fore.MAGENTA + f"[{time.strftime('%H:%M:%S')}] Аккаунт: {name} | {response_message}")
                else:
                    print(Fore.RED + f"[{time.strftime('%H:%M:%S')}] Аккаунт: {name} | Токен: {token[:10]} | Прокси: {proxy} | Ошибка: {response_message}")

            # Задержка между аккаунтами
            delay = random.uniform(min_delay, max_delay)
            print(Fore.YELLOW + f"[{time.strftime('%H:%M:%S')}] Задержка перед следующим аккаунтом: {delay:.2f} секунд")
            time.sleep(delay)

        # Пауза между циклами
        if pause_between_cycles:
            print(Fore.GREEN + f"[{time.strftime('%H:%M:%S')}] Повтор отправки сообщений через {restart_time}.")
            time.sleep(pause_between_cycles)

if __name__ == "__main__":
    main()
