class StorageErrors(Exception):

    def __init__(self, message, filename=None, lineno=None):
        self.message = message
        self.filename = filename
        self.lineno = lineno
        super().__init__(self.message)

    def __str__(self):
        return f"{self.message} while starting the app in {self.filename} at line {self.lineno}"

