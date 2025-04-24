from flask import (
    Flask,
    render_template,
    request,
    redirect,
    send_from_directory,
    jsonify,
)
from database import Database
from functions import (
    insert_student,
    add_assignment as add_assignment_auto,
    view_assignments_by_building,
    view_rooms_with_availability,
    available_rooms_by_prefs,
    compatible_students_by_prefs,
    building_report,
)
import os

# ── one-time seed on first launch ──────────────────────────────────────────────────────────────────────────
if os.environ.get("WERKZEUG_RUN_MAIN") is None:
    tmp = Database()
    tmp.connect()
    tmp.init_database()
    tmp.seed_data()
    tmp.disconnect()
    print("Database seeded")

# ── global DB connection ───────────────────────────────────────────────────────────────────────────────────
db = Database()
db.connect()

# ── Flask setup ────────────────────────────────────────────────────────────────────────────────────────────
app = Flask(
    __name__,
    static_folder="../front_end",
    template_folder="../front_end",
)

# ── basic navigation pages ─────────────────────────────────────────────────────────────────────────────────
@app.route("/")
@app.route("/start")
def start():
    return render_template("start.html")


@app.route("/functions")
def functions_page():
    return render_template("functions.html")

# ── form pages ─────────────────────────────────────────────────────────────────────────────────────────────
@app.route("/add_student")
def add_student():
    return render_template("menu_options_websites/add_student.html")


@app.route("/add_assignment")
def add_assignment():
    return render_template("menu_options_websites/add_assignment.html")

# ── report / view pages ────────────────────────────────────────────────────────────────────────────────────
@app.route("/view_assignments")
def view_assignments():
    return render_template("menu_options_websites/view_assignments.html")


@app.route("/view_rooms")
def view_rooms():
    return render_template("menu_options_websites/view_rooms.html")


@app.route("/available_rooms")
def available_rooms():
    return render_template("menu_options_websites/available_rooms.html")


@app.route("/compatible_students")
def compatible_students():
    return render_template("menu_options_websites/compatible_students.html")


@app.route("/building_report")
def building_report_page():
    return render_template("menu_options_websites/building_report.html")


@app.route("/bonus_query")
def bonus_query():
    return render_template("menu_options_websites/bonus_query.html")

# ── static assets ─────────────────────────────────────────────────────────────────────────────────────────
@app.route("/style.css")
def style_css():
    return send_from_directory(app.static_folder, "style.css")


@app.route("/style2.css")
def style2_css():
    return send_from_directory(
        os.path.join(app.static_folder, "menu_options_websites"), "style2.css"
    )


@app.route("/buttonnoise.mp3")
def buttonnoise():
    return send_from_directory(app.static_folder, "buttonnoise.mp3")

# ── utility endpoint ──────────────────────────────────────────────────────────────────────────────────────
@app.route("/check_student")
def check_student():
    name = request.args.get("name", "").strip()
    db.execute("SELECT 1 FROM Student WHERE Name = ?", (name,))
    return jsonify({"exists": db.fetchone() is not None})

# ── form submission: add student ──────────────────────────────────────────────────────────────────────────
@app.route("/submit_student", methods=["POST"])
def submit_student_form():
    try:
        name = request.form["name"].strip()
        ac = int("ac" in request.form)
        dining = int("dining" in request.form)
        kitchen = int("kitchen" in request.form)
        private = int("private" in request.form)
        insert_student(db, name, ac, dining, kitchen, private)
        return redirect("/functions")
    except Exception as e:
        return f"Insert failed: {e}", 500

# ── JSON: auto-assign a room ──────────────────────────────────────────────────────────────────────────────
@app.route("/assign_room", methods=["POST"])
def assign_room():
    data = request.get_json(force=True, silent=True) or {}
    name = data.get("name", "").strip()
    if not name:
        return "Missing student name", 400
    try:
        return add_assignment_auto(db, name)
    except Exception as e:
        return f"Assignment failed: {e}", 500

# ── JSON: assignments by building ─────────────────────────────────────────────────────────────────────────
@app.route("/api/assignments")
def api_assignments():
    bmap = {"east": 1, "south": 2, "west": 3}
    key = request.args.get("building", "").lower()
    if key not in bmap:
        return "Unknown building", 400
    rows = view_assignments_by_building(db, bmap[key])
    return jsonify([dict(r) for r in rows])

# ── JSON: rooms with availability ─────────────────────────────────────────────────────────────────────────
@app.route("/api/rooms")
def api_rooms():
    bmap = {"east": 1, "south": 2, "west": 3}
    key = request.args.get("building", "").lower()
    if key not in bmap:
        return "Unknown building", 400
    rows = view_rooms_with_availability(db, bmap[key])
    return jsonify([dict(r) for r in rows])

# ── JSON: available rooms by preference ───────────────────────────────────────────────────────────────────
@app.route("/api/available_rooms")
def api_available_rooms():
    wants_kitchen = int(request.args.get("wants_kitchen", 0))
    wants_private = int(request.args.get("wants_private", 0))
    bmap = {1: "east", 2: "south", 3: "west"}
    data = available_rooms_by_prefs(db, wants_kitchen, wants_private)
    payload = {bmap[b]: rooms for b, rooms in data.items()}
    return jsonify(payload)

# ── JSON: compatible students ─────────────────────────────────────────────────────────────────────────────
@app.route("/api/compatible_students")
def api_compatible_students():
    flags = {
        "wants_ac": int(request.args.get("wants_ac", 0)),
        "wants_dining": int(request.args.get("wants_dining", 0)),
        "wants_kitchen": int(request.args.get("wants_kitchen", 0)),
        "wants_private": int(request.args.get("wants_private", 0)),
    }
    rows = compatible_students_by_prefs(db, **flags)
    return jsonify([dict(r) for r in rows])

# ── JSON: building report ─────────────────────────────────────────────────────────────────────────────────
@app.route("/api/building_report")
def api_building_report():
    rows, campus_total = building_report(db)
    return jsonify({"rows": [dict(r) for r in rows], "campus_total": campus_total})

# ── run the app ───────────────────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        app.run(debug=True, port=8080)
    finally:
        db.disconnect()
#──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────