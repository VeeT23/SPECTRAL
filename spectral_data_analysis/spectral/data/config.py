import json
import os

DEFAULT_CONFIG = {
    "course_filepath":"test.png"
}

class Config:
    def __init__(self, path="config.json"):
        self.path = path
        self.data = self._load()

        print(self.data)


    def _load(self):
        if not os.path.exists(self.path):
            return DEFAULT_CONFIG.copy()
        with open(self.path, "r") as f:
            return json.load(f)

    
    def save(self):
        with open(self.path, "w") as f:
            json.dump(self.config, f, indent=4)