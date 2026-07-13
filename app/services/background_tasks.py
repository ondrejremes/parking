import logging
from datetime import datetime, timedelta
from sqlalchemy import and_
from app.database import SessionLocal
from app import models
from app.models.enums import SpotType
from app.services import email_notifications

logger = logging.getLogger(__name__)


async def send_reservation_reminders():
    """
    Background task: Pošli reminder emaily den před rezervací
    - Pro všechny rezervace (přidělená i sdílená místa)
    - Kolem 19:00 (spouští se večer)
    """
    db = SessionLocal()
    try:
        # Zítra
        tomorrow = datetime.now().date() + timedelta(days=1)

        # Najdi všechny rezervace na zítřejší den
        reservations = db.query(models.Reservation).filter(
            and_(
                models.Reservation.date == tomorrow,
                models.Reservation.cancelled_at == None,
            )
        ).all()

        logger.info(f"🔍 Hledám reminder emaily na {tomorrow}: {len(reservations)} rezervací")

        for reservation in reservations:
            # Zajdi místo a uživatele
            spot = db.query(models.Spot).filter_by(id=reservation.spot_id).first()
            user = db.query(models.User).filter_by(id=reservation.user_id).first()

            if not spot or not user:
                continue

            logger.info(f"📧 Posílám reminder: {user.email} - {spot.floor}/{spot.number}")

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

        logger.info(f"✅ Remindery poslány ({len(reservations)} emailů)")

    except Exception as e:
        logger.error(f"❌ Chyba v send_reservation_reminders: {e}", exc_info=True)
    finally:
        db.close()
