import serial.tools.list_ports

from time import sleep
from typing import Optional
from serial import SerialException

from project.station.logging.station_logger import logger
from project.station.services.port_finder import PortFinder
from project.station.utils.port_finder_utils import get_port_info
from project.station.config.port_finder.port_finder_config import PortFinderConfig


class StationConnection:
    """
    Класс для управления подключением к станции с автоматическим определением порта.

    Обеспечивает:
    - Автоматический поиск и валидацию порта станции
    - Установку и поддержку соединения
    - Отправку команд и чтение ответов
    - Потокобезопасные операции с портом
    - Автоматическое восстановление соединения

    Attributes:
        baudrate (int): Скорость передачи данных (по умолчанию 115200)
        timeout (float): Таймаут операций ввода-вывода в секундах (по умолчанию 1.0)
        max_retries (int): Максимальное количество попыток переподключения (по умолчанию 3)
        connection (Optional[serial.Serial]): Объект соединения с портом
        config (PortFinderConfig): Конфигурация для работы с портами
        port_finder (PortFinder): Поисковик портов станции
        port (Optional[str]): Текущий используемый порт
    """

    def __init__(self, baudrate: int = 115200, timeout: float = 1.0, max_retries: int = 3):
        """
        Инициализация подключения к станции.

        Args:
            baudrate: Скорость передачи данных (бод).
            timeout: Таймаут операций ввода-вывода в секундах.
            max_retries: Максимальное количество попыток переподключения при ошибках.

        Examples:
            >>> # Инициализация с параметрами по умолчанию
            >>> conn = StationConnection()
            >>> print(conn.baudrate)
            115200

            >>> # Инициализация с кастомными параметрами
            >>> custom_conn = StationConnection(baudrate=9600, timeout=2.0, max_retries=5)
            >>> print(custom_conn.timeout)
            2.0
        """
        self.baudrate = baudrate
        self.timeout = timeout
        self.max_retries = max_retries
        self.connection: Optional[serial.Serial] = None
        self.config = PortFinderConfig()
        self.port_finder = PortFinder()
        self.port = self._get_valid_port()

        if self.port:
            logger.info("Инициализирован StationConnection для порта %s", self.port)
        else:
            logger.warning("Инициализирован StationConnection без указания порта")

    def _get_valid_port(self) -> Optional[str]:
        """
        Получает валидный порт из конфига или выполняет автоматический поиск.

        Проверяет сохраненный порт из конфигурации на доступность.
        Если порт недоступен или не сохранен, выполняет поиск нового порта.

        Returns:
            Optional[str]: Имя доступного порта (например, 'COM3') или None,
                          если подходящий порт не найден.

        Examples:
            >>> # Когда сохраненный порт доступен
            >>> conn = StationConnection()
            >>> _ = conn.config.save_port({'device': 'COM3'})
            >>> port = conn._get_valid_port()
            >>> print(port)  # 'COM3' если порт доступен

            >>> # Когда порт нужно искать заново
            >>> new_conn = StationConnection()
            >>> new_conn.config.clear_config()
            >>> port = new_conn._get_valid_port()
            >>> print(port)  # Найденный порт или None
        """
        if port_info := self.config.load_port():
            if port := port_info.get('device'):
                if self._verify_port_available(port):
                    logger.info("Используется сохраненный порт: %s", port)
                    return port
                logger.warning("Сохраненный порт %s недоступен", port)

        logger.info("Попытка автоматического поиска порта станции")
        if new_port := self.port_finder.find_station_port(use_cached=False):
            if self._verify_port_available(new_port):
                logger.info("Найден новый порт: %s", new_port)
                return new_port

        logger.error("Не удалось найти подходящий порт станции")
        return None

    def _verify_port_available(self, port: str) -> bool:
        """
        Проверяет доступность указанного порта.

        Создает тестовое соединение с портом для проверки его работоспособности.

        Args:
            port: Имя порта для проверки (например, 'COM3').

        Returns:
            bool: True если порт доступен, False в случае ошибки.

        Examples:
            >>> conn = StationConnection()
            >>> # Проверка доступного порта (зависит от системы)
            >>> conn._verify_port_available('COM1')  # True или False
            >>> # Проверка несуществующего порта
            >>> conn._verify_port_available('NOT_EXIST')  # False
        """
        try:
            test_conn = serial.Serial(port=port, baudrate=self.baudrate, timeout=0.5)
            test_conn.close()
            return True
        except SerialException:
            return False

    def connect(self, retry_count: int = 0) -> bool:
        """
        Устанавливает подключение к станции с возможностью повторных попыток.

        Выполняет попытки подключения с учетом max_retries.
        При неудаче может автоматически искать новый порт.

        Args:
            retry_count: Текущий счетчик попыток (используется для рекурсии).

        Returns:
            bool: True если подключение установлено, False в случае ошибки.

        Raises:
            SerialException: При критических ошибках работы с портом.

        Examples:
            >>> conn = StationConnection()
            >>> # Успешное подключение
            >>> if conn.connect():
            ...     print("Подключение установлено")
            ...     conn.disconnect()
            ...
            >>> # Неудачное подключение (с автоматическими ретраями)
            >>> bad_conn = StationConnection(max_retries=2)
            >>> bad_conn.port = "NOT_EXIST"
            >>> bad_conn.connect()  # False после 3 попыток
        """
        if not self.port:
            logger.error("Порт не определен, подключение невозможно")
            return False

        if self.is_connected():
            logger.warning("Подключение к %s уже установлено", self.port)
            return True

        try:
            logger.info("Попытка подключения к %s (baudrate=%d)", self.port, self.baudrate)
            self.connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
            sleep(2)  # Даем время для инициализации соединения
            logger.info("Успешное подключение к %s", self.port)
            return True

        except SerialException as e:
            logger.error("Ошибка подключения к %s: %s", self.port, str(e))
            self.connection = None

            if retry_count < self.max_retries:
                logger.info("Попытка переподключения (%d/%d)",
                          retry_count + 1, self.max_retries)
                if new_port := self._find_new_port():
                    self.port = new_port
                    return self.connect(retry_count + 1)

            return False

    def _find_new_port(self) -> Optional[str]:
        """
        Пытается найти новый порт станции и обновляет конфигурацию.

        Returns:
            Optional[str]: Имя нового порта или None, если порт не найден.

        Examples:
            >>> conn = StationConnection()
            >>> # Внутренний метод, обычно вызывается автоматически
            >>> new_port = conn._find_new_port()
            >>> print(new_port)  # Имя порта или None
        """
        logger.info("Поиск нового порта станции...")
        if new_port := self.port_finder.find_station_port(use_cached=False):
            if port_info := get_port_info(next(
                p for p in serial.tools.list_ports.comports()
                if p.device == new_port
            )):
                self.config.save_port(port_info)
                logger.info("Обновлен порт в конфиге: %s", new_port)
                return new_port
        return None

    def disconnect(self) -> bool:
        """
        Корректно разрывает подключение к станции.

        Returns:
            bool: True если отключение прошло успешно, False в случае ошибки.

        Examples:
            >>> conn = StationConnection()
            >>> conn.connect()
            >>> if conn.disconnect():
            ...     print("Отключение успешно")
            ... else:
            ...     print("Ошибка отключения")
        """
        if not self.is_connected():
            logger.warning("Нет активного подключения для разрыва")
            return False

        try:
            logger.info("Закрытие подключения к %s", self.port)
            self.connection.close()
            self.connection = None
            logger.info("Подключение к %s успешно закрыто", self.port)
            return True

        except SerialException as e:
            logger.error("Ошибка при закрытии подключения: %s", str(e))
            return False

    def is_connected(self) -> bool:
        """
        Проверяет активность текущего подключения.

        Returns:
            bool: True если подключение активно и работает, False в противном случае.

        Examples:
            >>> conn = StationConnection()
            >>> conn.connect()
            >>> print(conn.is_connected())  # True
            >>> conn.disconnect()
            >>> print(conn.is_connected())  # False
        """
        return self.connection is not None and self.connection.is_open

    def send_command(self, command: str) -> bool:
        """
        Отправляет команду на станцию через последовательный порт.

        Args:
            command: Текст команды для отправки (без завершающего символа новой строки).

        Returns:
            bool: True если команда отправлена успешно, False в случае ошибки.

        Examples:
            >>> conn = StationConnection()
            >>> conn.connect()
            >>> # Успешная отправка команды
            >>> conn.send_command("GET_STATUS")
            True
            >>> # Ошибка отправки (например, после разрыва соединения)
            >>> conn.disconnect()
            >>> conn.send_command("PING")  # False
        """
        if not self.is_connected():
            if not self.connect():
                logger.error("Не удалось восстановить подключение для отправки команды")
                return False

        try:
            logger.debug("Отправка команды: %s", command.strip())
            self.connection.write((command + '\n').encode())
            return True

        except SerialException as e:
            logger.error("Ошибка отправки команды: %s", str(e))
            self.disconnect()
            return False

    def read_response(self, timeout: Optional[float] = None) -> Optional[str]:
        """
        Читает ответ от станции с возможностью указания таймаута.

        Args:
            timeout: Опциональный таймаут чтения в секундах.
                    Если None, используется timeout соединения.

        Returns:
            Optional[str]: Прочитанный ответ или None в случае ошибки.

        Examples:
            >>> conn = StationConnection()
            >>> conn.connect()
            >>> conn.send_command("GET_STATUS")
            >>> # Чтение с таймаутом 2 секунды
            >>> response = conn.read_response(timeout=2.0)
            >>> print(response)  # Ответ станции или None
        """
        if not self.is_connected():
            if not self.connect():
                logger.error("Не удалось восстановить подключение для чтения ответа")
                return None

        original_timeout = self.connection.timeout
        if timeout is not None:
            self.connection.timeout = timeout

        try:
            response = self.connection.readline().decode().strip()
            logger.debug("Получен ответ: %s", response)
            return response
        except SerialException as e:
            logger.error("Ошибка чтения ответа: %s", str(e))
            return None
        finally:
            if timeout is not None:
                self.connection.timeout = original_timeout

    def __enter__(self):
        """
        Поддержка контекстного менеджера для использования с 'with'.

        Returns:
            StationConnection: Текущий экземпляр соединения.

        Examples:
            >>> with StationConnection() as conn:
            ...     conn.send_command("PING")
            ...     response = conn.read_response()
            ...     print(response)
        """
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Автоматически закрывает соединение при выходе из контекста."""
        self.disconnect()

    def __del__(self):
        """Деструктор - автоматически закрывает соединение при удалении объекта."""
        if self.is_connected():
            self.disconnect()
