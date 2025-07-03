from enum import Enum
from fastapi import FastAPI, Response, status, Request
from fastapi.staticfiles import StaticFiles
from urllib.parse import unquote
import requests
import logging
import os

app = FastAPI()

# Serve static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")


# Get environment vars
ELK46_USERNAME = str(os.getenv("ELK46_USERNAME"))
ELK46_PASSWORD = str(os.getenv("ELK46_PASSWORD"))
ELK46_NUMBER = str(os.getenv("ELK46_NUMBER"))

HOST_URL = str(os.getenv("HOST_URL"))


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Message(str, Enum):
    percy1 = "percy1"
    percy2 = "percy2"
    percy3 = "percy3"
    someone1 = "someone1"
    someone2 = "someone2"
    someone3 = "someone3"


@app.post("/sms/request", responses={status.HTTP_500_INTERNAL_SERVER_ERROR: {}})
def send_request_sms(to: str):
    """
    Send a (two-way) SMS to the given [number] and ask if we can call them.
    Register a response URL for if the user responds "okay".
    """
    logger.info(f"Asking for permission to call {to}.")

    res = requests.post(
        "https://api.46elks.com/a1/sms",
        auth=(ELK46_USERNAME, ELK46_PASSWORD),
        data={
            "from": ELK46_NUMBER,
            "to": to,
            "message": "Är det okej att vi ringer upp dig? Svara 'okej' isåfall."
        }
    )
    if res.status_code != status.HTTP_200_OK:
        logger.error(f"Failed to send request SMS to {to}; {res.text}")
        return Response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/sms/final", responses={status.HTTP_500_INTERNAL_SERVER_ERROR: {}})
def send_final_sms(to: str):
    """
    Send a SMS to the given number nudging them to order tickets for the upcoming games.
    """
    logger.info(f"Sending final SMS to {to}.")

    res = requests.post(
        "https://api.46elks.com/a1/sms",
        auth=(ELK46_USERNAME, ELK46_PASSWORD),
        data={
            "from": ELK46_NUMBER,
            "to": to,
            "message": "Här kommer länken jag pratade om! \nhttps://youtu.be/gtZAjLyrM30?si=laMjoa_7lXT7HViC"
        }
    )
    if res.status_code != status.HTTP_200_OK:
        logger.error(f"Failed to send final SMS to {to}; {res.text}")
        return Response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    


@app.post("/sms/receive", responses={status.HTTP_400_BAD_REQUEST: {}})
async def receive_sms(request: Request):
    """
    Receive responses to any SMS:s sent.
    If a user responds "okay" to if we may call them, perform a call.
    """
    # By some reason, 46elks sends a body that looks like a HTTP path parameter list, and FastAPI expects JSON.
    body = unquote((await request.body()).decode("utf-8"))
    params: dict[str, str] = {}
    for val in body.split("&"):
        parts = val.split("=")
        params[parts[0]] = parts[1]
    
    if "to" not in params or "from" not in params or "message" not in params:
        logger.error(f"SMS data received from 46elks is missing fields; {params}")
        return Response(status.HTTP_422_UNPROCESSABLE_ENTITY)

    to: str = params["to"]
    from_: str = params["from"]
    message: str = params["message"]


    if not to == ELK46_NUMBER:
        logger.error(f"Received SMS from {from_} was sent to {to} and not to our allocated 46elks number.")
        return Response(status.HTTP_400_BAD_REQUEST)
    
    # Maybe we need some way to check that we recently asked for permission to call, so that we don"t just call every time to user writes "okay".
    # TODO: Check for more variations
    if message.lower() in ["okay", "ok", "sure", "yes", "okej", "ja", "visst", "absolut"]:
        # TODO: Obtain which message the user wants somehow
        res = send_call(from_, Message.percy1)
        if res.status_code != status.HTTP_200_OK:
            return Response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        logger.info(f"Call permission denied for {from_}.")
    
    return Response() # We have to return a response with an empty body, otherwise 46elks will forward the body as a message to the user.


def send_call(to: str, message: Message) -> requests.Response:
    """
    Call the given [number] and deliver the selected message [m].
    When the user hangs up, send them a final SMS.
    """
    logger.info(f"Calling {to} and delivering message {message.value}.")

    res = requests.post(
        "https://api.46elks.com/a1/calls",
        auth=(ELK46_USERNAME, ELK46_PASSWORD),
        data={
            "from": ELK46_NUMBER,
            "to": to,
            "voice_start": f'{{"play": "{HOST_URL}/static/audio/{message.value}.mp3"}}',
            "whenhangup": f"{HOST_URL}/sms/final?to={to}"
        }
    )
    if res.status_code != status.HTTP_200_OK:
        logger.error(f"Failed to call {to}; {res.text}")
    return res
    
    


# Note to self:
# To query upcoming games, we can use
# GET https://www.malmoredhawks.com/api/sports-v2/game-schedule?seasonUuid=xs4m9qupsi&seriesUuid=qQ9-bb0bzEWUk&gameTypeUuid=qQ9-af37Ti40B&gamePlace=home&played=all
