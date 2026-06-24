from datetime import date
from app.config import ACS_CONNECTION_STRING, EMAIL_FROM
from app.models.enums import Shift

_SHIFT_LABEL = {
    Shift.FULL_DAY: "celý den",
    Shift.DAY: "denní směna (8:00–18:00)",
    Shift.NIGHT: "noční směna (18:00–09:00)",
}


def send_confirmation(to_email: str, spot_floor: str, spot_number: str, day: date, shift: Shift):
    if not ACS_CONNECTION_STRING:
        return
    _send(
        to=to_email,
        subject=f"Potvrzení rezervace parkoviště — {day}",
        body=(
            f"Vaše rezervace byla potvrzena.\n\n"
            f"Místo: patro {spot_floor}, č. {spot_number}\n"
            f"Datum: {day}\n"
            f"Směna: {_SHIFT_LABEL[shift]}\n"
        ),
    )


def send_reminder(to_email: str, spot_floor: str, spot_number: str, day: date, shift: Shift):
    if not ACS_CONNECTION_STRING:
        return
    _send(
        to=to_email,
        subject=f"Připomenutí rezervace parkoviště — {day}",
        body=(
            f"Zítra máte rezervované parkovací místo.\n\n"
            f"Místo: patro {spot_floor}, č. {spot_number}\n"
            f"Datum: {day}\n"
            f"Směna: {_SHIFT_LABEL[shift]}\n"
        ),
    )


def _send(to: str, subject: str, body: str):
    from azure.communication.email import EmailClient

    client = EmailClient.from_connection_string(ACS_CONNECTION_STRING)
    client.begin_send({
        "senderAddress": EMAIL_FROM,
        "recipients": {"to": [{"address": to}]},
        "content": {"subject": subject, "plainText": body},
    })
