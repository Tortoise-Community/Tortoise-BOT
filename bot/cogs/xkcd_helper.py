import requests
import random
import re


class XKCD:

    def __init__(self):
        self._latest = "https://xkcd.com/info.0.json"
        self.latest_data = requests.get("https://xkcd.com/info.0.json").json()

    def _data_helper(self, num=None):
        if (not num):
            r = requests.get(f"https://xkcd.com/info.0.json").json()
            transcript_data = re.findall("(\w+)(\s)", r["transcript"])
            num = r["num"]
            data = {
                "Month": r["month"],
                "Day": r["day"],
                "Year Made": r["year"],
                "Comic Number": r["num"],
                "Transcript": "".join([f"{y[0]}{y[1]}" for y in [x for x in transcript_data]]) if r["transcript"] else "No transcript available",
                "Image Link": r["img"],
                "Comic Link": f"https://xkcd.com/{num}",
                "Title": r["title"],
                "Number": r["num"]
            }

            return data
        elif (not (not num)):
            r = requests.get(f"https://xkcd.com/{num}/info.0.json").json()
            transcript_data = re.findall("(\w+)(\s)", r["transcript"])
            data = {
                "Month": r["month"],
                "Day": r["day"],
                "Year Made": r["year"],
                "Comic Number": r["num"],
                "Transcript": "".join([f"{y[0]}{y[1]}" for y in [x for x in transcript_data]]) if r["transcript"] else "No transcript available",
                "Image Link": r["img"],
                "Comic Link": f"https://xkcd.com/{num}",
                "Title": r["title"],
                "Number": r["num"]
            }

            return data

    def _random_helper(self):
        rand = random.randint(1, self.latest_data["num"] + 1)
        r = requests.get(f"https://xkcd.com/{rand}/info.0.json").json()
        transcript_data = re.findall("(\w+)(\s)", r["transcript"])
        num = r["num"]
        ok = {
            "Month": r["month"],
            "Day": r["day"],
            "Year Made": r["year"],
            "Comic Number": r["num"],
            "Transcript": "".join([f"{y[0]}{y[1]}" for y in [x for x in transcript_data]]) if r["transcript"] else "No transcript available",
            "Image Link": r["img"],
            "Comic Link": f"https://xkcd.com/{num}",
            "Title": r["title"],
            "Number": r["num"]
        }

        return ok

    def grab(self, num: str):
        r = requests.get(f"https://xkcd.com/{num}/info.0.json").json()
        img_url = r["img"]
        return img_url

    def latest(self):
        data = self.latest_data["img"]
        return data

    def random(self):
        return self._random_helper()["Image Link"]

    def grab_data(self, num: str):
        return self._data_helper(num=num)

    def grab_latest_data(self):
        return self._data_helper()

    def random_data(self):
        return self._random_helper()
