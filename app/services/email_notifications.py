import logging
from datetime import datetime
from html import escape
from app.config import ACS_CONNECTION_STRING, EMAIL_FROM, BASE_URL
from azure.communication.email import EmailClient

logger = logging.getLogger(__name__)

# Whitelist pro testování - jen tyto emaily budou dostávat notifikace
EMAIL_WHITELIST = {
    "ondrej.remes@alintrust.cz",
}

# Nastavit na False až budeme hotovi s testováním
WHITELIST_ENABLED = True


def should_send_email(email: str) -> bool:
    """Zjistit, jestli by se měl email poslat (kontrola whitelistu)"""
    if not WHITELIST_ENABLED:
        return True
    return email.lower() in {e.lower() for e in EMAIL_WHITELIST}


async def send_reservation_confirmation(user_email: str, user_name: str, spot: dict, date: str, shift: str):
    """Potvrzení vytvoření rezervace"""
    if not should_send_email(user_email):
        logger.debug(f"Email {user_email} není na whitelistu, notifikace poslána není")
        return

    shift_name = {"FULL_DAY": "Celý den", "DAY": "Denní směna", "NIGHT": "Noční směna"}.get(shift, shift)
    shift_time = {"FULL_DAY": "00:00-24:00", "DAY": "06:00-18:00", "NIGHT": "18:00-00:00"}.get(shift, "")

    from datetime import datetime as dt
    date_obj = dt.strptime(date, "%d.%m.%Y")
    calendar_url = f"{BASE_URL}/calendar/week?week={date_obj.isoformat()}"

    subject = "Potvrzení rezervace parkovacího místa"
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif;">
            <p>Dobrý den,</p>
            <p>vaše rezervace parkovacího místa byla úspěšně vytvořena.</p>

            <table style="border-collapse: collapse; margin: 20px 0;">
                <tr>
                    <td style="padding: 8px;"><strong>📍 Místo:</strong></td>
                    <td style="padding: 8px;">Patro {spot.get('floor')}, Místo {spot.get('number')}</td>
                </tr>
                <tr>
                    <td style="padding: 8px;"><strong>📅 Datum:</strong></td>
                    <td style="padding: 8px;">{date}</td>
                </tr>
                <tr>
                    <td style="padding: 8px;"><strong>⏰ Čas:</strong></td>
                    <td style="padding: 8px;">{shift_name} ({shift_time})</td>
                </tr>
                <tr>
                    <td style="padding: 8px;"><strong>🚗 Typ:</strong></td>
                    <td style="padding: 8px;">{spot.get('spot_type', 'Sdílené')}</td>
                </tr>
            </table>

            <p>Pokud chcete rezervaci zrušit, můžete tak učinit v aplikaci minimálně 24 hodin před termínem.</p>

            <p style="margin-top: 30px;">
                <a href="{calendar_url}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">🔗 Otevřít v aplikaci</a>
            </p>

            <hr style="margin: 30px 0;">
            <p style="color: #666; font-size: 12px;">Parkování App | Alintrust</p>
        </body>
    </html>
    """

    plain_text = f"""Dobrý den,

vaše rezervace parkovacího místa byla úspěšně vytvořena.

📍 Parkovací místo: Patro {spot.get('floor')}, Místo {spot.get('number')}
📅 Datum: {date}
⏰ Čas: {shift_name} ({shift_time})
🚗 Typ: {spot.get('spot_type', 'Sdílené')}

Pokud chcete rezervaci zrušit, můžete tak učinit v aplikaci minimálně 24 hodin před termínem.

Parkování App
Alintrust"""

    await _send_email(user_email, subject, html_content, plain_text)


async def send_reservation_cancellation(user_email: str, user_name: str, spot: dict, date: str, shift: str):
    """Oznámení zrušení rezervace"""
    if not should_send_email(user_email):
        logger.debug(f"Email {user_email} není na whitelistu, notifikace poslána není")
        return

    shift_name = {"FULL_DAY": "Celý den", "DAY": "Denní směna", "NIGHT": "Noční směna"}.get(shift, shift)

    from datetime import datetime as dt
    date_obj = dt.strptime(date, "%d.%m.%Y")
    calendar_url = f"{BASE_URL}/calendar/week?week={date_obj.isoformat()}"

    subject = "Zrušení rezervace parkovacího místa"
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif;">
            <p>Dobrý den,</p>
            <p>vaše rezervace parkovacího místa byla zrušena.</p>

            <table style="border-collapse: collapse; margin: 20px 0;">
                <tr>
                    <td style="padding: 8px;"><strong>📍 Místo:</strong></td>
                    <td style="padding: 8px;">Patro {spot.get('floor')}, Místo {spot.get('number')}</td>
                </tr>
                <tr>
                    <td style="padding: 8px;"><strong>📅 Datum:</strong></td>
                    <td style="padding: 8px;">{date}</td>
                </tr>
                <tr>
                    <td style="padding: 8px;"><strong>⏰ Čas:</strong></td>
                    <td style="padding: 8px;">{shift_name}</td>
                </tr>
            </table>

            <p>Pokud jste si rezervaci zrušili omylem, můžete si místo znovu rezervovat v aplikaci.</p>

            <p style="margin-top: 30px;">
                <a href="{calendar_url}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">🔗 Otevřít v aplikaci</a>
            </p>

            <hr style="margin: 30px 0;">
            <p style="color: #666; font-size: 12px;">Parkování App | Alintrust</p>
        </body>
    </html>
    """

    plain_text = f"""Dobrý den,

vaše rezervace parkovacího místa byla zrušena.

📍 Parkovací místo: Patro {spot.get('floor')}, Místo {spot.get('number')}
📅 Datum: {date}
⏰ Čas: {shift_name}

Pokud jste si rezervaci zrušili omylem, můžete si místo znovu rezervovat v aplikaci.

Parkování App
Alintrust"""

    await _send_email(user_email, subject, html_content, plain_text)


async def send_spot_release_notification(user_email: str, user_name: str, spot: dict, date: str, shift: str, released_by: str):
    """Oznámení uvolnění místa"""
    if not should_send_email(user_email):
        logger.debug(f"Email {user_email} není na whitelistu, notifikace poslána není")
        return

    shift_name = {"FULL_DAY": "Celý den", "DAY": "Denní směna", "NIGHT": "Noční směna"}.get(shift, shift)

    from datetime import datetime as dt
    date_obj = dt.strptime(date, "%d.%m.%Y")
    calendar_url = f"{BASE_URL}/calendar/week?week={date_obj.isoformat()}"

    subject = "Vaše přidělené místo bylo uvolněno do sdíleného poolu"
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif;">
            <p>Dobrý den,</p>
            <p>vaše přidělené parkovací místo bylo uvolněno do sdíleného poolu a je nyní dostupné dalším zaměstnancům.</p>

            <table style="border-collapse: collapse; margin: 20px 0;">
                <tr>
                    <td style="padding: 8px;"><strong>📍 Místo:</strong></td>
                    <td style="padding: 8px;">Patro {spot.get('floor')}, Místo {spot.get('number')}</td>
                </tr>
                <tr>
                    <td style="padding: 8px;"><strong>📅 Datum:</strong></td>
                    <td style="padding: 8px;">{date}</td>
                </tr>
                <tr>
                    <td style="padding: 8px;"><strong>⏰ Čas:</strong></td>
                    <td style="padding: 8px;">{shift_name}</td>
                </tr>
                <tr>
                    <td style="padding: 8px;"><strong>👤 Uvolnil/a:</strong></td>
                    <td style="padding: 8px;">{released_by}</td>
                </tr>
            </table>

            <p>Své místo si můžete znovu přidělit v aplikaci.</p>

            <p style="margin-top: 30px;">
                <a href="{calendar_url}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">🔗 Otevřít v aplikaci</a>
            </p>

            <hr style="margin: 30px 0;">
            <p style="color: #666; font-size: 12px;">Parkování App | Alintrust</p>
        </body>
    </html>
    """

    plain_text = f"""Dobrý den,

vaše přidělené parkovací místo bylo uvolněno do sdíleného poolu a je nyní dostupné dalším zaměstnancům.

📍 Parkovací místo: Patro {spot.get('floor')}, Místo {spot.get('number')}
📅 Datum: {date}
⏰ Čas: {shift_name}
👤 Uvolnil/a: {released_by}

Své místo si můžete znovu přidělit v aplikaci.

Parkování App
Alintrust"""

    await _send_email(user_email, subject, html_content, plain_text)


async def send_reservation_reminder(user_email: str, user_name: str, spot: dict, date: str, shift: str):
    """Připomenutí den před rezervací (jen přidělená místa)"""
    if not should_send_email(user_email):
        logger.debug(f"Email {user_email} není na whitelistu, notifikace poslána není")
        return

    shift_name = {"FULL_DAY": "Celý den", "DAY": "Denní směna", "NIGHT": "Noční směna"}.get(shift, shift)

    from datetime import datetime as dt
    date_obj = dt.strptime(date, "%d.%m.%Y")
    calendar_url = f"{BASE_URL}/calendar/week?week={date_obj.isoformat()}"

    subject = "Připomenutí: Vaše rezervace parkovacího místa je zítra"
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif;">
            <p>Dobrý den,</p>
            <p>připomínáme vám, že máte zítra zarezervované parkovací místo.</p>

            <table style="border-collapse: collapse; margin: 20px 0;">
                <tr>
                    <td style="padding: 8px;"><strong>📍 Místo:</strong></td>
                    <td style="padding: 8px;">Patro {spot.get('floor')}, Místo {spot.get('number')}</td>
                </tr>
                <tr>
                    <td style="padding: 8px;"><strong>📅 Datum:</strong></td>
                    <td style="padding: 8px;">{date}</td>
                </tr>
                <tr>
                    <td style="padding: 8px;"><strong>⏰ Čas:</strong></td>
                    <td style="padding: 8px;">{shift_name}</td>
                </tr>
            </table>

            <p>Pokud se nemůžete dostavit, zrušte si prosím rezervaci v aplikaci, aby místo mohli využít ostatní.</p>

            <p style="margin-top: 30px;">
                <a href="{calendar_url}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">🔗 Otevřít v aplikaci</a>
            </p>

            <hr style="margin: 30px 0;">
            <p style="color: #666; font-size: 12px;">Parkování App | Alintrust</p>
        </body>
    </html>
    """

    plain_text = f"""Dobrý den,

připomínáme vám, že máte zítra zarezervované parkovací místo.

📍 Parkovací místo: Patro {spot.get('floor')}, Místo {spot.get('number')}
📅 Datum: {date}
⏰ Čas: {shift_name}

Pokud se nemůžete dostavit, zrušte si prosím rezervaci v aplikaci, aby místo mohli využít ostatní.

Parkování App
Alintrust"""

    await _send_email(user_email, subject, html_content, plain_text)


async def _send_email(to_email: str, subject: str, html_content: str, plain_text: str):
    """Poslat email přes Azure Communication Services"""
    try:
        if not ACS_CONNECTION_STRING:
            logger.warning("ACS_CONNECTION_STRING není nastaven, email není poslán")
            return

        client = EmailClient.from_connection_string(ACS_CONNECTION_STRING)

        message = {
            "senderAddress": EMAIL_FROM,
            "recipients": {
                "to": [{"address": to_email}],
            },
            "content": {
                "subject": subject,
                "plainText": plain_text,
                "html": html_content,
            },
        }

        poller = client.begin_send(message)
        result = poller.result()

        logger.info(f"✉️ Email poslán na {to_email}: {subject}")
        logger.debug(f"   Message ID: {result}")

    except Exception as e:
        logger.error(f"❌ Chyba při odesílání emailu na {to_email}: {e}", exc_info=True)


async def send_guest_parking_confirmation(user_email: str, user_name: str, guest_name: str, guest_plate: str,
                                          guest_company: str, guest_contact: str, spot: dict, date: str,
                                          time_from: str, time_to: str):
    """Potvrzení vytvoření rezervace pro hosta"""
    if not should_send_email(user_email):
        logger.debug(f"Email {user_email} není na whitelistu, notifikace poslána není")
        return

    from datetime import datetime as dt
    date_obj = dt.strptime(date, "%d.%m.%Y")
    calendar_url = f"{BASE_URL}/calendar/week?week={date_obj.isoformat()}"

    # Escape user inputs to prevent HTML injection
    safe_guest_name = escape(guest_name)
    safe_guest_plate = escape(guest_plate or "neuvedeno")
    safe_guest_company = escape(guest_company or "neuvedeno")
    safe_guest_contact = escape(guest_contact or "neuvedeno")

    subject = "Potvrzení rezervace parkovacího místa pro hosta"
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif;">
            <p>Dobrý den,</p>
            <p>rezervace parkovacího místa pro hosta byla úspěšně vytvořena.</p>

            <table style="border-collapse: collapse; margin: 20px 0;">
                <tr>
                    <td style="padding: 8px;"><strong>👤 Host:</strong></td>
                    <td style="padding: 8px;">{safe_guest_name}</td>
                </tr>
                <tr>
                    <td style="padding: 8px;"><strong>🚗 SPZ:</strong></td>
                    <td style="padding: 8px;">{safe_guest_plate}</td>
                </tr>
                <tr>
                    <td style="padding: 8px;"><strong>🏢 Společnost:</strong></td>
                    <td style="padding: 8px;">{safe_guest_company}</td>
                </tr>
                <tr>
                    <td style="padding: 8px;"><strong>📞 Kontakt:</strong></td>
                    <td style="padding: 8px;">{safe_guest_contact}</td>
                </tr>
                <tr>
                    <td style="padding: 8px;"><strong>📍 Místo:</strong></td>
                    <td style="padding: 8px;">Patro {spot.get('floor')}, Místo {spot.get('number')}</td>
                </tr>
                <tr>
                    <td style="padding: 8px;"><strong>📅 Datum:</strong></td>
                    <td style="padding: 8px;">{date}</td>
                </tr>
                <tr>
                    <td style="padding: 8px;"><strong>⏰ Čas:</strong></td>
                    <td style="padding: 8px;">{time_from} – {time_to}</td>
                </tr>
            </table>

            <p>Pokud chcete rezervaci zrušit, můžete to udělat v aplikaci.</p>

            <p style="margin-top: 30px;">
                <a href="{calendar_url}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">🔗 Otevřít v aplikaci</a>
            </p>

            <hr style="margin: 30px 0;">
            <p style="color: #666; font-size: 12px;">Parkování App | Alintrust</p>
        </body>
    </html>
    """

    plain_text = f"""Dobrý den,

rezervace parkovacího místa pro hosta byla úspěšně vytvořena.

👤 Host: {safe_guest_name}
🚗 SPZ: {safe_guest_plate}
🏢 Společnost: {safe_guest_company}
📞 Kontakt: {safe_guest_contact}
📍 Parkovací místo: Patro {spot.get('floor')}, Místo {spot.get('number')}
📅 Datum: {date}
⏰ Čas: {time_from} – {time_to}

Pokud chcete rezervaci zrušit, můžete to udělat v aplikaci.

Parkování App
Alintrust"""

    await _send_email(user_email, subject, html_content, plain_text)
