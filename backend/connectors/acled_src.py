import time
import requests
import pathway as pw
from datetime import datetime


class AcledSource(pw.io.python.ConnectorSubject):
    def __init__(self,api_key:str,email:str,polling_interval:int=3600):
        super().__init__()
        self.api_key = api_key
        self.email = email
        self.polling_interval = polling_interval
        self.base_url = "https://api.acleddata.com/acled/read"

    def run(self):
        while True:
            try:
                params={
                    "key": self.api_key,
                    "email": self.email,
                    "limit": 50,  # Max records per request
                    "fields":"json"

                }
                response=requests.get(self.base_url,params=params)
                response.raise_for_status()
                data=response.json()

                if data.get("success") and "data" in data:
                    for event in data["data"]:

                        location=event.get("location",'Unknown')
                        country=event.get("country",'Unknown')
                        notes=event.get("notes",'No details provided.')
                        event_type=event.get("event_type",'Conflict Event')

                        text_content=f"[{event_type}] in {location}, {country}: {notes}"
                        url="https://acleddata.com/dashboard/"


                        try:
                            dt=datetime.strptime(event['event_data'],"%Y-%m-%d")
                            timestamp=int(dt.timestamp())
                        except:
                            timestamp=time.time()

                        out_event={
                            "source":"ACLED Conflict Data",
                            "text":text_content,
                            "url":url,
                            "timestamp":float(timestamp),
                            "bias":"Neutral"
                        }

                        self.next(out_event)

            except Exception as e:
                    print(f"⚠️ ACLED API error: {e}")
                
            time.sleep(self.polling_interval)