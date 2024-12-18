import logging
import sys
from typing import Optional

class Logger:
    _instance: Optional[logging.Logger] = None

    @classmethod
    def setup(cls, log_level: str = "INFO", log_file: Optional[str] = None):
        """Setup logger instance"""
        if cls._instance is None:
            logger = logging.getLogger("OpenHands_TSB")
            logger.setLevel(getattr(logging, log_level.upper()))

            # Console handler
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(
                logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            )
            logger.addHandler(console_handler)

            # File handler if specified
            if log_file:
                file_handler = logging.FileHandler(log_file)
                file_handler.setFormatter(
                    logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                )
                logger.addHandler(file_handler)

            cls._instance = logger

    @classmethod
    def get_logger(cls) -> logging.Logger:
        """Get logger instance"""
        if cls._instance is None:
            cls.setup()
        return cls._instance
