import os
import sys
import logging

from typing import Final
from logging.handlers import RotatingFileHandler


class LoggerConfig:
    """
    Конфигурация логгера.

    Содержит все настраиваемые параметры для системы логирования:
    - Пути к файлам логов
    - Уровни логирования
    - Форматы вывода
    - Параметры ротации логов

    Attributes:
        LOG_DIR: Директория для хранения лог-файлов
        LOG_FILE: Имя основного лог-файла
        LOG_LEVEL: Уровень логирования (по умолчанию DEBUG)
        MAX_BYTES: Максимальный размер лог-файла перед ротацией (5MB)
        LOG_FORMAT: Формат строки лога
        LOGGER_NAME: Имя корневого логгера
        DATE_FORMAT: Формат даты/времени в логах
        BACKUP_COUNT: Количество сохраняемых архивных лог-файлов
    """
    LOG_DIR: Final[str] = 'station/logging'
    LOG_FILE: Final[str] = 'station.log'
    LOG_LEVEL: Final[int] = logging.DEBUG
    MAX_BYTES: Final[int] = 5 * 1024 * 1024
    LOG_FORMAT: Final[str] = '%(asctime)s - %(levelname)s - %(message)s'
    LOGGER_NAME: Final[str] = 'ledger_app'
    DATE_FORMAT: Final[str] = '%Y-%m-%d %H:%M:%S'
    BACKUP_COUNT: Final[int] = 3


class LoggerFactory:
    """
    Фабрика для создания и настройки логгера.

    Предоставляет методы для:
    - Создания форматтера логов
    - Обеспечения существования лог-директории
    - Создания обработчиков (файловый и консольный)
    - Полной настройки логгера
    """

    @staticmethod
    def create_formatter() -> logging.Formatter:
        """
        Создает форматтер логов с заданным форматом.

        Returns:
            logging.Formatter: Форматтер с настроенным форматом вывода и даты.

        Examples:
            >>> formatter = LoggerFactory.create_formatter()
            >>> isinstance(formatter, logging.Formatter)
            True
        """
        return logging.Formatter(
            LoggerConfig.LOG_FORMAT,
            datefmt=LoggerConfig.DATE_FORMAT
        )

    @staticmethod
    def ensure_log_directory() -> None:
        """
        Создает директорию для логов, если она не существует.

        Raises:
            OSError: Если не удалось создать директорию.

        Examples:
            >>> LoggerFactory.ensure_log_directory()
            >>> os.path.exists(LoggerConfig.LOG_DIR)
            True
        """
        os.makedirs(LoggerConfig.LOG_DIR, exist_ok=True)

    @staticmethod
    def create_file_handler() -> RotatingFileHandler:
        """
        Создает файловый обработчик с ротацией логов.

        Returns:
            RotatingFileHandler: Настроенный обработчик для записи в файл.

        Examples:
            >>> handler = LoggerFactory.create_file_handler()
            >>> isinstance(handler, RotatingFileHandler)
            True
        """
        LoggerFactory.ensure_log_directory()
        handler = RotatingFileHandler(
            filename=os.path.join(LoggerConfig.LOG_DIR, LoggerConfig.LOG_FILE),
            maxBytes=LoggerConfig.MAX_BYTES,
            backupCount=LoggerConfig.BACKUP_COUNT,
            encoding='utf-8'
        )
        handler.setFormatter(LoggerFactory.create_formatter())
        return handler

    @staticmethod
    def create_console_handler() -> logging.StreamHandler:
        """
        Создает консольный обработчик для вывода в stdout.

        Returns:
            logging.StreamHandler: Настроенный консольный обработчик.

        Examples:
            >>> handler = LoggerFactory.create_console_handler()
            >>> isinstance(handler, logging.StreamHandler)
            True
        """
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(LoggerFactory.create_formatter())
        return handler

    @staticmethod
    def setup_logger() -> logging.Logger:
        """
        Настраивает и возвращает готовый к использованию логгер.

        Выполняет:
        - Создание нового логгера
        - Установку уровня логирования
        - Добавление файлового и консольного обработчиков
        - Отключение пропагации сообщений в родительские логгеры

        Returns:
            logging.Logger: Полностью настроенный логгер приложения.

        Examples:
            >>> logger = LoggerFactory.setup_logger()
            >>> logger.name == LoggerConfig.LOGGER_NAME
            True
            >>> len(logger.handlers)
            2
        """
        app_logger = logging.getLogger(LoggerConfig.LOGGER_NAME)

        app_logger.handlers.clear()

        app_logger.setLevel(LoggerConfig.LOG_LEVEL)

        app_logger.addHandler(LoggerFactory.create_file_handler())
        app_logger.addHandler(LoggerFactory.create_console_handler())

        app_logger.propagate = False

        return app_logger


logger: logging.Logger = LoggerFactory.setup_logger()
