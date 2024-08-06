import os


class Config:
    DEFAULT_APPMAP_COMMAND = "appmap"
    DEFAULT_CLEAN = False

    appmap_command = os.getenv("APPMAP_COMMAND", DEFAULT_APPMAP_COMMAND)
    clean = os.getenv("APPMAP_NAVIE_CLEAN", str(DEFAULT_CLEAN))

    @staticmethod
    def get_appmap_command():
        return Config.appmap_command

    @staticmethod
    def set_appmap_command(command):
        Config.appmap_command = command

    @staticmethod
    def get_clean():
        return Config.clean.lower() == "true"

    @staticmethod
    def set_clean(clean):
        Config.clean = clean
