"""Admin reports and exports."""
from datetime import datetime, time, timedelta

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from ..auth import require_admin
from ..database import get_db
from ..errors import AppError
from ..models import Booking, Room, User
from ..services.export import generate_export

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/usage-report")
def usage_report(
    from_date: str = Query(..., alias="from"),
    to_date: str = Query(..., alias="to"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    try:
        start_day = datetime.strptime(from_date, "%Y-%m-%d").date()
        end_day = datetime.strptime(to_date, "%Y-%m-%d").date()
    except ValueError:
        raise AppError(400, "INVALID_BOOKING_WINDOW", "Invalid date range")

    if end_day < start_day:
        raise AppError(400, "INVALID_BOOKING_WINDOW", "Invalid date range")

    start_dt = datetime.combine(start_day, time.min)
    end_dt = datetime.combine(end_day + timedelta(days=1), time.min)

    rooms = (
        db.query(Room)
        .filter(Room.org_id == admin.org_id)
        .order_by(Room.id.asc())
        .all()
    )

    result_rooms = []
    for room in rooms:
        bookings = (
            db.query(Booking)
            .filter(
                Booking.room_id == room.id,
                Booking.status == "confirmed",
                Booking.start_time >= start_dt,
                Booking.start_time < end_dt,
            )
            .all()
        )
        result_rooms.append(
            {
                "room_id": room.id,
                "room_name": room.name,
                "confirmed_bookings": len(bookings),
                "revenue_cents": sum(b.price_cents for b in bookings),
            }
        )

    return {"from": from_date, "to": to_date, "rooms": result_rooms}


@router.get("/export")
def export_bookings(
    room_id: int | None = None,
    include_all: bool = False,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if room_id is not None:
        room = (
            db.query(Room)
            .filter(Room.id == room_id, Room.org_id == admin.org_id)
            .first()
        )
        if room is None:
            raise AppError(404, "ROOM_NOT_FOUND", "Room not found")

    csv_body = generate_export(db, admin.org_id, admin.id, room_id, include_all)
    return Response(content=csv_body, media_type="text/csv")
