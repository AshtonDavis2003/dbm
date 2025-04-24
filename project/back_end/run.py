# project/back_end/run.py
from server import app

if __name__ == "__main__":
    import os
    port = int(os.getenv("PORT", 8080))
    # bind to 0.0.0.0 instead of the default 127.0.0.1
    app.run(host="0.0.0.0", port=port, debug=True)
