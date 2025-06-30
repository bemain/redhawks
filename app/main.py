from enum import Enum
from fastapi import FastAPI, Query, Response
from fastapi.staticfiles import StaticFiles
import datetime
import requests
import os

app = FastAPI()

# Serve static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")


# Get environment vars
ELK46_USERNAME = str(os.getenv("ELK46_USERNAME"))
ELK46_PASSWORD = str(os.getenv("ELK46_PASSWORD"))
ELK46_NUMBER = str(os.getenv("ELK46_NUMBER"))

HOST_URL = str(os.getenv("HOST_URL"))



class Message(str, Enum):
    percy1 = "percy1"
    percy2 = "percy2"
    percy3 = "percy3"
    someone1 = "someone1"
    someone2 = "someone2"
    someone3 = "someone3"


@app.post("/sms/request")
def send_request_sms(to: str, response: Response):
    """
    Send a (two-way) SMS to the given [number] and ask if we can call them.
    Register a response URL for if the user responds "okay".
    """
    res = requests.post(
        "https://api.46elks.com/a1/sms",
        auth=(ELK46_USERNAME, ELK46_PASSWORD),
        data={
            "from": ELK46_NUMBER,
            "to": to,
            "message": "Är det okej att vi ringer upp dig? Svara 'okej' isåfall."
        }
    )
    response.status_code = res.status_code
    print(res.text)


@app.post("/sms/final")
def send_final_sms(to: str, response: Response):
    """
    Send a SMS to the given number nudging them to order tickets for the upcoming games.
    """
    res = requests.post(
        "https://api.46elks.com/a1/sms",
        auth=(ELK46_USERNAME, ELK46_PASSWORD),
        data={
            "from": ELK46_NUMBER,
            "to": to,
            "message": "Här kommer länken jag pratade om!"
        }
    )
    response.status_code = res.status_code
    print(res.text)


@app.post("/sms/receive")
def receive_sms(
    id: str,
    message: str = "",
    from_number: str = Query(alias="from"),
    to: str | None = None,
    direction: str = "incoming",
    created: datetime.datetime | None = None
):
    """
    Receive responses to any SMS:s sent.
    If a user responds "okay" to if we may call them, perform a call.
    """
    print(to)

    if not to == ELK46_NUMBER:
        return
    
    # Maybe we need some way to check that we recently asked for permission to call, so that we don"t just call every time to user writes "okay".
    # TODO: Check for more variations
    if message.lower() in ["okay", "ok", "sure", "yes", "okej"]:
        # TODO: Obtain which message the user wants somehow
        send_call(from_number, Message.percy1)


def send_call(to: str, message: Message):
    """
    Call the given [number] and deliver the selected message [m].
    When the user hangs up, send them a final SMS.
    """
    response = requests.post(
        "https://api.46elks.com/a1/calls",
        auth=(ELK46_USERNAME, ELK46_PASSWORD),
        data={
            "from": ELK46_NUMBER,
            "to": to,
            "voice_start": {"play": f"{HOST_URL}/static/audio/{message.value}.mp3"},
            "whenhangup": f"{HOST_URL}/sms/final?to={to}"
        }
    )
    print(response.text)
    
    


# Note to self:
# To query upcoming games, we can use
# GET https://www.malmoredhawks.com/api/sports-v2/game-schedule?seasonUuid=xs4m9qupsi&seriesUuid=qQ9-bb0bzEWUk&gameTypeUuid=qQ9-af37Ti40B&gamePlace=home&played=all
