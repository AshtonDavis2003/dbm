# run.py ─ entry point from the project root
import os
from server import app          # server.py is in the same folder

if __name__ == "__main__":
    app.run(debug=True, port=8080)
