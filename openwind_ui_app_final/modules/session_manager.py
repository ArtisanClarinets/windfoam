
import json
import pandas as pd
from datetime import datetime

def save_session(bore_df, temperature, humidity, material_props, notes=""):
    session = {
        "timestamp": datetime.now().isoformat(),
        "notes": notes,
        "bore_profile": bore_df.to_dict(orient="records"),
        "environment": {"temperature": temperature, "humidity": humidity},
        "material": material_props or {}
    }
    return json.dumps(session, indent=2)

def load_session(json_string):
    session_data = json.loads(json_string)
    bore_df = pd.DataFrame(session_data["bore_profile"])
    temperature = session_data["environment"].get("temperature", 22)
    humidity = session_data["environment"].get("humidity", 50)
    material_props = session_data.get("material", {})
    notes = session_data.get("notes", "")
    return bore_df, temperature, humidity, material_props, notes
