import logging
import asyncio
from datetime import datetime, timedelta
from sqlalchemy import and_
from app.database import SessionLocal
from app import models
from app.models.enums import SpotType
from app.services import email_notifications

logger = logging.getLogger(__name__)


async def _send_reservation_reminders_async():
    """
    Background task: Pošli reminder emaily den před rezervací
    - Pro všechny rezervace (přidělená i sdílená místa)
    - Pro přidělená místa (bez rezervace)
    - Kolem 19:00 (spouští se večer)
    """
    db = SessionLocal()
    try:
        # Zítra
        tomorrow = datetime.now().date() + timedelta(days=1)

        logger.info(f"🔍 Hledám reminder emaily na {tomorrow}")

        sent_count = 0

        # 1. Najdi všechny rezervace na zítřejší den
        reservations = db.query(models.Reservation).filter(
            and_(
                models.Reservation.date == tomorrow,
                models.Reservation.cancelled_at == None,
            )
        ).all()

        for reservation in reservations:
            # Zajdi místo a uživatele
            spot = db.query(models.Spot).filter_by(id=reservation.spot_id).first()
            user = db.query(models.User).filter_by(id=reservation.user_id).first()

            if not spot or not user or not user.email:
                continue

            logger.info(f"📧 Posílám reminder (rezervace): {user.email} - {spot.floor}/{spot.number}")

            # Pošli reminder
            spot_dict = {
                "floor": spot.floor,
                "number": spot.number,
                "spot_type": spot.spot_type.value if spot.spot_type else "Sdílené"
            }

            await email_notifications.send_reservation_reminder(
                user.email,
                user.display_name,
                spot_dict,
                tomorrow.strftime("%d.%m.%Y"),
                reservation.shift.value
            )
            sent_count += 1

        # 2. Najdi všechna přidělená místa (pro uživatele bez rezervace na zítřek)
        assigned_spots = db.query(models.Spot).filter(
            and_(
                models.Spot.assigned_user_id != None,
                models.Spot.active == True,
            )
        ).all()

        for spot in assigned_spots:
            user = db.query(models.User).filter_by(id=spot.assigned_user_id).first()

            if not user or not user.email:
                continue

            # Kontrola: má uživatel už rezervaci na zítřek na jiném místě?
            existing_reservation = db.query(models.Reservation).filter(
                and_(
                    models.Reservation.user_id == user.id,
                    models.Reservation.date == tomorrow,
                    models.Reservation.cancelled_at == None,
                )
            ).first()

            if existing_reservation:
                # Už má rezervaci, neposílej duplikát
                continue

            logger.info(f"📧 Posílám reminder (přidělené místo): {user.email} - {spot.floor}/{spot.number}")

            spot_dict = {
                "floor": spot.floor,
                "number": spot.number,
                "spot_type": "Přidělené"
            }

            await email_notifications.send_reservation_reminder(
                user.email,
                user.display_name,
                spot_dict,
                tomorrow.strftime("%d.%m.%Y"),
                "FULL_DAY"
            )
            sent_count += 1

        # 3. Najdi všechna guest parkings na zítřek
        guest_parkings = db.query(models.GuestParking).filter(
            and_(
                models.GuestParking.date == tomorrow,
                models.GuestParking.cancelled_at == None,
            )
        ).all()

        for gp in guest_parkings:
            user = db.query(models.User).filter_by(id=gp.created_by_user_id).first()
            spot = db.query(models.Spot).filter_by(id=gp.spot_id).first()

            if not user or not user.email or not spot:
                continue

            logger.info(f"📧 Posílám reminder (guest parking): {user.email} - {gp.guest_name} na {spot.floor}/{spot.number}")

            spot_dict = {
                "floor": spot.floor,
                "number": spot.number,
            }

            await email_notifications.send_guest_parking_reminder(
                user.email,
                user.display_name,
                gp.guest_name,
                spot_dict,
                tomorrow.strftime("%d.%m.%Y"),
                gp.time_from.strftime("%H:%M"),
                gp.time_to.strftime("%H:%M")
            )
            sent_count += 1

        logger.info(f"✅ Remindery poslány ({sent_count} emailů)")

    except Exception as e:
        logger.error(f"❌ Chyba v send_reservation_reminders: {e}", exc_info=True)
    finally:
        db.close()


def send_reservation_reminders():
    """Synchronní wrapper pro APScheduler — spouští async funkci v event loopu."""
    try:
        asyncio.run(_send_reservation_reminders_async())
    except RuntimeError as e:
        if "asyncio.run() cannot be called from a running event loop" in str(e):
            logger.info("Scheduler běží v event loopu, používám create_task")
            loop = asyncio.get_event_loop()
            loop.create_task(_send_reservation_reminders_async())
        else:
            raise
