from project.station.controllers.station_connection import StationConnection

# Вариант 1: Ручное управление подключением
conn = StationConnection(baudrate=115200)  # Порт берется автоматически из конфига
if conn.connect():
    try:
        conn.send_command("M114")  # Пример команды
        response = conn.read_response()
    finally:
        conn.disconnect()

# Вариант 2: Использование контекстного менеджера
with StationConnection() as conn:  # Все параметры по умолчанию
    if conn.is_connected():
        conn.send_command("G28")  # Пример команды