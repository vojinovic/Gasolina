import json
from datetime import datetime

with open("fuel_prices.json", "r") as file:
    data = json.load(file)

# TEST update
data["countries"][0]["diesel"] = 1.69
data["countries"][0]["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")

with open("fuel_prices.json", "w") as file:
    json.dump(data, file, indent=2)

print("Fuel prices updated!")
