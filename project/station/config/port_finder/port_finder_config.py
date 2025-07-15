import json
import threading

from pathlib import Path
from typing import Dict, Optional

from project.station.logging.station_logger import logger


class PortFinderConfig:
    """
    Класс для управления конфигурацией поиска портов станции.

    Обеспечивает сохранение, загрузку и очистку информации о порте
    в JSON-файле конфигурации. Автоматически создает необходимые директории,
    поддерживает потокобезопасность и валидацию данных.

    Attributes:
        config_dir (Path): Директория, в которой хранится файл конфигурации.
        config_file (str): Имя файла конфигурации.
        config_path (Path): Полный путь к файлу конфигурации.
    """

    CONFIG_DIR = "project/station/config/port_finder"
    CONFIG_FILE = "port_finder.json"

    def __init__(
        self,
        config_dir: Optional[str] = None,
        config_file: Optional[str] = None,
    ):
        """
        Инициализирует конфигурацию поиска портов.

        Создает необходимые директории и формирует полный путь к файлу конфигурации.
        Поддерживает пользовательские значения директории и имени файла.

        Args:
            config_dir: Пользовательский путь к директории конфигурации.
                        Если не указан, используется значение CONFIG_DIR.
            config_file: Пользовательское имя файла конфигурации.
                         Если не указано, используется значение CONFIG_FILE.

        Examples:
            >>> # Использование путей по умолчанию
            >>> config = PortFinderConfig()
            >>> print(config.config_path)
            project/station/config/port_finder/port_finder.json

            >>> # Использование пользовательских путей
            >>> custom_config = PortFinderConfig(
            ...     config_dir="/tmp/my_station",
            ...     config_file="custom_port.json"
            ... )
            >>> print(custom_config.config_path)
            /tmp/my_station/custom_port.json
        """
        self._lock = threading.Lock()
        self.config_dir = Path(config_dir or self.CONFIG_DIR)
        self.config_file = config_file or self.CONFIG_FILE
        self.config_path = self.config_dir / self.config_file
        self._ensure_config_dir_exists()

    def _ensure_config_dir_exists(self) -> None:
        """
        Проверяет и создает директорию для хранения конфигурации.

        Создает все промежуточные директории, если они не существуют.
        В случае ошибки логирует и пробрасывает исключение.

        Raises:
            Exception: Если не удалось создать директорию.

        Examples:
            >>> config = PortFinderConfig()
            >>> config._ensure_config_dir_exists()
            >>> # Директория будет создана, если не существует
            >>> assert config.config_dir.exists()
        """
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            logger.debug("Проверена директория конфига: %s", self.config_dir)
        except Exception as e:
            logger.error("Ошибка создания директории конфига: %s", str(e))
            raise

    def save_port(self, port_info: Dict[str, str]) -> bool:
        """
        Сохраняет информацию о порте в JSON-файл конфигурации.

        Выполняет базовую валидацию входных данных и блокирует доступ
        к файлу на время записи для потокобезопасности.

        Args:
            port_info: Словарь с информацией о порте, обязательно содержащий:
                      - 'device': имя порта (например, 'COM3')
                      - Дополнительные метаданные о порте (опционально)

        Returns:
            bool: True если сохранение прошло успешно, False в случае ошибки.

        Examples:
            >>> config = PortFinderConfig()
            >>> # Успешное сохранение
            >>> port_data = {'device': 'COM3', 'description': 'Main station port'}
            >>> config.save_port(port_data)
            True

            >>> # Ошибка валидации - отсутствует 'device'
            >>> invalid_data = {'description': 'No device specified'}
            >>> config.save_port(invalid_data)
            False
        """
        if not isinstance(port_info, dict) or "device" not in port_info:
            logger.error("Неверный формат port_info: отсутствует ключ 'device'")
            return False

        with self._lock:
            try:
                with open(self.config_path, "w", encoding="utf-8") as f:
                    json.dump(port_info, f, indent=2, ensure_ascii=False)
                logger.info("Информация о порте сохранена в %s", self.config_path)
                logger.debug("Сохраненные данные: %s", port_info)
                return True
            except Exception as e:
                logger.error("Ошибка сохранения конфига порта: %s", str(e))
                return False

    def load_port(self) -> Optional[Dict[str, str]]:
        """
        Загружает информацию о порте из JSON-файла конфигурации.

        Безопасно читает файл в потокобезопасном режиме.

        Returns:
            Optional[Dict[str, str]]: Словарь с информацией о порте вида:
                                     {'device': 'COM3', ...} или None,
                                     если файл не существует или произошла ошибка.

        Examples:
            >>> config = PortFinderConfig()
            >>> # Загрузка существующего конфига
            >>> _ = config.save_port({'device': 'COM4', 'baud': '9600'})
            >>> port_info = config.load_port()
            >>> print(port_info)
            {'device': 'COM4', 'baud': '9600'}

            >>> # Загрузка несуществующего конфига
            >>> new_config = PortFinderConfig(config_file="nonexistent.json")
            >>> new_config.load_port() is None
            True
        """
        with self._lock:
            try:
                if not self.config_path.exists():
                    logger.debug("Конфигурационный файл не существует")
                    return None

                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                logger.info("Загружена информация о порте из %s", self.config_path)
                logger.debug("Загруженные данные: %s", data)
                return data
            except json.JSONDecodeError as e:
                logger.error("Некорректный JSON в конфигурационном файле: %s", str(e))
                return None
            except Exception as e:
                logger.error("Ошибка загрузки конфига порта: %s", str(e))
                return None

    def clear_config(self) -> bool:
        """
        Очищает конфигурационный файл, записывая в него пустой словарь.

        Выполняется в потокобезопасном режиме.

        Returns:
            bool: True если очистка прошла успешно, False в случае ошибки.

        Examples:
            >>> config = PortFinderConfig()
            >>> _ = config.save_port({'device': 'COM5'})
            >>> config.clear_config()
            True
            >>> # После очистки файл существует, но пуст
            >>> config.load_port()
            {}
        """
        with self._lock:
            try:
                with open(self.config_path, "w", encoding="utf-8") as f:
                    json.dump({}, f, indent=2, ensure_ascii=False)
                logger.info("Конфигурационный файл очищен: %s", self.config_path)
                return True
            except Exception as e:
                logger.error("Ошибка очистки конфигурационного файла: %s", str(e))
                return False
