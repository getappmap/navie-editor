import os
from typing import Optional


class Config:
    DEFAULT_APPMAP_COMMAND = "appmap"
    DEFAULT_CLEAN = False
    DEFAULT_TRAJECTORY_FILE = None

    appmap_command = os.getenv("APPMAP_COMMAND", DEFAULT_APPMAP_COMMAND).split()
    clean = os.getenv("APPMAP_NAVIE_CLEAN", str(DEFAULT_CLEAN))
    trajectory_file = os.getenv("APPMAP_NAVIE_TRAJECTORY_FILE", None)

    @staticmethod
    def get_appmap_command() -> list[str]:
        return Config.appmap_command

    @staticmethod
    def set_appmap_command(command):
        Config.appmap_command = command

    @staticmethod
    def get_clean() -> bool:
        return Config.clean.lower() == "true"

    @staticmethod
    def set_clean(clean):
        Config.clean = clean

    @staticmethod
    def get_trajectory_file() -> Optional[str]:
        return Config.trajectory_file

    @staticmethod
    def set_trajectory_file(trajectory_file):
        Config.trajectory_file = trajectory_file
