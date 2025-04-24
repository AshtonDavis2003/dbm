from tabulate import tabulate
from database import Database

# ── Student insert ──────────────────────────────────────────────────────
def insert_student(
    db: Database,
    name: str,
    wants_ac: int,
    wants_dining: int,
    wants_kitchen: int,
    wants_private: int,
) -> None:
    db.execute("SELECT COALESCE(MAX(StudentId), 0) + 1 FROM Student")
    next_id = db.fetchone()[0]

    db.execute(
        """
        INSERT INTO Student (StudentId, Name, WantsAC, WantsDining,
                             WantsKitchen, WantsPrivateBathroom)
        VALUES (?,?,?,?,?,?)
        """,
        (next_id, name, wants_ac, wants_dining, wants_kitchen, wants_private),
    )

    db.execute("SELECT * FROM Student ORDER BY StudentId")
    rows = db.fetchall()
    headers = ["StudentId", "Name", "AC", "Dining", "Kitchen", "PrivateBath"]
    print("\n" + tabulate(rows, headers=headers, tablefmt="fancy_grid"))

# ── Room auto-assignment ──────────────────────────────────────────────────────
def add_assignment(db: Database, name: str) -> str:
    db.execute(
        """
        SELECT StudentId, WantsKitchen, WantsPrivateBathroom
          FROM Student
         WHERE Name = ?
        """,
        (name,),
    )
    row = db.fetchone()
    if not row:
        return "Student not found."

    student_id, wants_kitchen, wants_private = row

    db.execute(
        """
        SELECT BuildingId, RoomNumber
          FROM Room
         WHERE HasKitchen = ? AND PrivateBathrooms = ?
           AND (BuildingId,RoomNumber) NOT IN
               (SELECT BuildingId, RoomNumber FROM Assignment)
         LIMIT 1
        """,
        (wants_kitchen, wants_private),
    )
    room = db.fetchone()

    note = "Assigned exact match."
    if not room:
        db.execute(
            """
            SELECT BuildingId, RoomNumber,
                   ABS(HasKitchen - ?) + ABS(PrivateBathrooms - ?) AS diff
              FROM Room
             WHERE (BuildingId,RoomNumber) NOT IN
                   (SELECT BuildingId, RoomNumber FROM Assignment)
             ORDER BY diff, BuildingId, RoomNumber
             LIMIT 1
            """,
            (wants_kitchen, wants_private),
        )
        room = db.fetchone()
        if not room:
            return "No rooms available."
        note = "Exact match not found. Assigned closest match."

    building_id, room_number = room[:2]

    db.execute(
        """
        INSERT OR REPLACE INTO Assignment (StudentId, BuildingId, RoomNumber)
        VALUES (?,?,?)
        """,
        (student_id, building_id, room_number),
    )

    db.execute(
        """
        SELECT A.StudentId, S.Name, A.BuildingId, A.RoomNumber
          FROM Assignment A
          JOIN Student S USING (StudentId)
         ORDER BY A.StudentId
        """
    )
    assignments = db.fetchall()
    print("\nCurrent Assignments")
    print(
        tabulate(
            assignments,
            headers=["StudentId", "Name", "BuildingId", "RoomNumber"],
            tablefmt="fancy_grid",
        )
    )

    return f"{note}  {name} → Building {building_id}, Room {room_number}."

# ── View assignments for one building ──────────────────────────────────────────────────────
def view_assignments_by_building(db: Database, building_id: int):
    db.execute(
        """
        SELECT S.Name, S.StudentId, A.RoomNumber
          FROM Assignment A
          JOIN Student S USING (StudentId)
         WHERE A.BuildingId = ?
         ORDER BY S.Name
        """,
        (building_id,),
    )
    return db.fetchall()

# ── Console helper: print all assignments ──────────────────────────────────────────────────────
def _print_assignments(db: Database) -> None:
    db.execute(
        """
        SELECT A.StudentId, S.Name, A.BuildingId, A.RoomNumber
          FROM Assignment A
          JOIN Student S USING (StudentId)
         ORDER BY A.StudentId
        """
    )
    print("\nCurrent Assignments")
    print(
        tabulate(
            db.fetchall(),
            headers=["StudentId", "Name", "Building", "Room"],
            tablefmt="fancy_grid",
        )
    )

# ── Rooms & availability for one building ──────────────────────────────────────────────────────
def view_rooms_with_availability(db: Database, building_id: int):
    db.execute(
        """
        SELECT R.RoomNumber,
               CASE WHEN A.StudentId IS NULL THEN 1 ELSE 0 END AS BedsAvailable
          FROM Room R
          LEFT JOIN Assignment A
                 ON A.BuildingId = R.BuildingId
                AND A.RoomNumber = R.RoomNumber
         WHERE R.BuildingId = ?
         ORDER BY R.BuildingId, R.RoomNumber
        """,
        (building_id,),
    )
    return db.fetchall()

# ── Available rooms filtered by kitchen/private prefs ────────────────────────────────────────────────────
def available_rooms_by_prefs(
    db: Database, wants_kitchen: int, wants_private: int
):
    db.execute(
        """
        SELECT R.BuildingId, R.RoomNumber
          FROM Room R
          LEFT JOIN Assignment A
                 ON A.BuildingId = R.BuildingId
                AND A.RoomNumber = R.RoomNumber
         WHERE A.StudentId IS NULL
           AND R.HasKitchen       = ?
           AND R.PrivateBathrooms = ?
         ORDER BY R.BuildingId, R.RoomNumber
        """,
        (wants_kitchen, wants_private),
    )
    rows = db.fetchall()
    result = {}
    for r in rows:
        result.setdefault(r["BuildingId"], []).append(r["RoomNumber"])
    return result

# ── Compatible students whose prefs exactly match given flags ──────────────────────────────────────────────────────
def compatible_students_by_prefs(
    db: Database,
    wants_ac: int,
    wants_dining: int,
    wants_kitchen: int,
    wants_private: int,
):
    db.execute(
        """
        SELECT Name, StudentId
          FROM Student
         WHERE WantsAC              = ?
           AND WantsDining          = ?
           AND WantsKitchen         = ?
           AND WantsPrivateBathroom = ?
         ORDER BY Name
        """,
        (wants_ac, wants_dining, wants_kitchen, wants_private),
    )
    return db.fetchall()

# ── Building-level summary of rooms & beds ──────────────────────────────────────────────────────
def building_report(db: Database):
    db.execute(
        """
        WITH PerRoom AS (
            SELECT R.BuildingId,
                   R.RoomNumber,
                   1                                   AS RoomBeds,
                   CASE WHEN A.StudentId IS NULL
                        THEN 1 ELSE 0 END             AS BedsFree
              FROM Room R
              LEFT JOIN Assignment A
                     ON A.BuildingId = R.BuildingId
                    AND A.RoomNumber = R.RoomNumber
        ),
        PerBuilding AS (
            SELECT B.BuildingId,
                   B.Name                             AS Building,
                   SUM(RoomBeds)                     AS TotalBeds,
                   COUNT(RoomNumber)                 AS TotalRooms,
                   SUM(CASE WHEN BedsFree > 0
                              THEN 1 ELSE 0 END)     AS RoomsWithSpace,
                   SUM(BedsFree)                     AS BedsAvailable
              FROM Building B
              JOIN PerRoom  P USING (BuildingId)
             GROUP BY B.BuildingId
        )
        SELECT Building,
               TotalBeds,
               TotalRooms,
               RoomsWithSpace,
               BedsAvailable
          FROM PerBuilding
         ORDER BY BuildingId
        """
    )
    rows = db.fetchall()
    campus_total = sum(r["BedsAvailable"] for r in rows)
    return rows, campus_total
#────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────