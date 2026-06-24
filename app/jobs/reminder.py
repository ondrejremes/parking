"""Daily reminder job — run via Container Apps Job at 07:00 UTC."""

from datetime import date, timedelta
from app.database import SessionLocal
from app import models
from app.services import email as email_service


def main():
    tomorrow = date.today() + timedelta(days=1)
    db = SessionLocal()
    try:
        reservations = (
            db.query(models.Reservation)
            .filter(
                models.Reservation.date == tomorrow,
                models.Reservation.cancelled_at.is_(None),
            )
            .all()
        )
        for res in reservations:
            user = db.query(models.User).filter_by(id=res.user_id).first()
            spot = db.query(models.Spot).filter_by(id=res.spot_id).first()
            if user and spot:
                email_service.send_reminder(user.email, spot.floor, spot.number, res.date, res.shift)
        print(f"Reminders sent: {len(reservations)}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
