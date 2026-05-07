from db_initializer import get_connection
from geopy.distance import geodesic
import random

MAX_FUEL = 2000
TARGET_MONEY = 3000
TOTAL_TURNS = 15


# --- HELPER FUNCTIONS ---

def get_airport_coordinates(ident):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(f"SELECT latitude_deg, longitude_deg FROM airport WHERE ident = '{ident}'")
    result = cursor.fetchone()
    connection.close()
    return result


def get_fuel_price(ident):
    """New helper to match your game.py needs"""
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(f"SELECT price_per_unit FROM fuel_price WHERE airport_ident = '{ident}'")
    result = cursor.fetchone()
    connection.close()
    return result[0] if result else 3.50


# --- CORE GAME LOGIC ---

def initialize_fuel_prices():
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT ident FROM airport WHERE continent = 'EU' AND type IN ('medium_airport', 'large_airport')")
    airports = cursor.fetchall()
    cursor.execute("DELETE FROM fuel_price")
    for airport in airports:
        price = round(random.uniform(1.5, 4.5), 2)
        cursor.execute(f"INSERT INTO fuel_price (airport_ident, price_per_unit) VALUES ('{airport[0]}', {price})")
    connection.commit()
    connection.close()


def create_game():
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        f"INSERT INTO game (difficulty, turns_total, turns_left, target_money, created_at) VALUES ('easy', {TOTAL_TURNS}, {TOTAL_TURNS}, {TARGET_MONEY}, NOW())")
    game_id = cursor.lastrowid
    connection.commit()
    connection.close()
    return game_id


def create_player(game_id, name):
    connection = get_connection()
    cursor = connection.cursor()
    # Fixed: Added city_name 'Helsinki' to initial creation
    cursor.execute(f"""
        INSERT INTO player (game_id, name, money, fuel, home_airport_ident, current_airport_ident, city_name) 
        VALUES ({game_id}, '{name}', 1000, 800, 'EFHK', 'EFHK', 'Helsinki')
    """)
    player_id = cursor.lastrowid
    connection.commit()
    connection.close()
    return player_id


def show_player(player_id, turns_left=None):
    """
    CRITICAL FIX: Added city_name to the SELECT.
    Now returns (name, money, fuel, ident, city_name)
    """
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(f"SELECT name, money, fuel, current_airport_ident, city_name FROM player WHERE id = {player_id}")
    player = cursor.fetchone()
    connection.close()
    return player


def get_contracts(player_id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(f"SELECT current_airport_ident FROM player WHERE id = {player_id}")
    current_airport_ident = cursor.fetchone()[0]
    current_coords = get_airport_coordinates(current_airport_ident)

    # Limit search to 40 for speed
    cursor.execute(
        f"SELECT ident, municipality, latitude_deg, longitude_deg FROM airport WHERE ident != '{current_airport_ident}' AND continent = 'EU' AND type IN ('medium_airport', 'large_airport') LIMIT 200")
    airports = cursor.fetchall()
    connection.close()

    airport_distances = []
    for airport in airports:
        dist = geodesic((current_coords[0], current_coords[1]), (airport[2], airport[3])).km
        airport_distances.append({"id": airport[0], "name": airport[1], "dist": int(dist)})

    # Pick 3 varied contracts
    try:
        choices = [
            random.choice([a for a in airport_distances if a["dist"] < 1000]),
            random.choice([a for a in airport_distances if 1000 <= a["dist"] < 2500]),
            random.choice([a for a in airport_distances if a["dist"] >= 2500])
        ]
    except IndexError:
        # Fallback if distances aren't perfectly distributed
        choices = random.sample(airport_distances, 3)

    contracts = []
    for c in choices:
        fuel_req = int(c["dist"] * 0.25)
        reward = int(round(c["dist"] * random.uniform(0.5, 0.8), 2))
        dest_coords = get_airport_coordinates(c["id"])

        contracts.append({
            "from": current_airport_ident,
            "to": c["id"],
            "destination_name": c["name"],
            "distance": c["dist"],
            "fuel_needed": fuel_req,
            "reward": reward,
            "lat": float(dest_coords[0]),  # Ensure these are floats, not strings
            "lng": float(dest_coords[1])
        })
    return contracts


def refuel_player(game_id, player_id, amount):
    """
    FIXED: Signature updated to match game.py call.
    Automatically fetches price from DB.
    """
    connection = get_connection()
    cursor = connection.cursor()

    # Get current price and current money
    cursor.execute(f"SELECT current_airport_ident, money, fuel FROM player WHERE id = {player_id}")
    player_data = cursor.fetchone()
    current_airport = player_data[0]
    current_money = player_data[1]
    current_fuel = player_data[2]

    price = get_fuel_price(current_airport)
    total_cost = amount * price

    if total_cost > current_money:
        connection.close()
        return "Not enough money to refuel that much!"

    if current_fuel + amount > MAX_FUEL:
        connection.close()
        return f"Tank capacity exceeded! Max capacity is {MAX_FUEL}."

    cursor.execute(f"UPDATE player SET money = money - {total_cost}, fuel = fuel + {amount} WHERE id = {player_id}")
    connection.commit()
    connection.close()
    return f"Refueled! Cost: {total_cost}€"


def update_player_after_contract(game_id, player_id, contract):
    """
    FIXED: Signature updated to match game.py call.
    Also updates the city_name column so the HUD stays correct!
    """
    connection = get_connection()
    cursor = connection.cursor()

    # We update current_airport AND city_name
    cursor.execute(f"""
        UPDATE player 
        SET money = money + {contract['reward']}, 
            fuel = fuel - {contract['fuel_needed']}, 
            current_airport_ident = '{contract['to']}',
            city_name = '{contract['destination_name'].replace("'", "''")}'
        WHERE id = {player_id}
    """)
    connection.commit()
    connection.close()
    return f"Flight to {contract['destination_name']} completed!"


def reduce_turn(game_id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(f"UPDATE game SET turns_left = turns_left - 1 WHERE id = {game_id}")
    connection.commit()
    connection.close()


def get_turns_left(game_id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(f"SELECT turns_left FROM game WHERE id = {game_id}")
    res = cursor.fetchone()
    connection.close()
    return res[0] if res else 0