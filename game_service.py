from db_initializer import get_connection
from geopy.distance import geodesic
import random
import os

MAX_FUEL = 2000
TARGET_MONEY = 3000
TOTAL_TURNS = 15

def clear_screen():
    print("\033c", end="")

def make_bar(value, maximum, length=20):
    filled = int((value / maximum) * length)
    empty = length - filled
    return "█" * filled + "░" * empty

def initialize_fuel_prices():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT ident
        FROM airport
        WHERE continent = 'EU'
        AND type IN ('medium_airport','large_airport')
    """)

    airports = cursor.fetchall()

    cursor.execute("DELETE FROM fuel_price")

    for airport in airports:
        ident = airport[0]

        price = round(random.uniform(2, 5), 2)

        cursor.execute(f"""
            INSERT INTO fuel_price (airport_ident, price_per_unit)
            VALUES ('{ident}', {price})
        """)

    connection.commit()
    connection.close()

def create_game():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(f"""
        INSERT INTO game (difficulty, turns_total, turns_left, target_money, created_at)
        VALUES ('easy', {TOTAL_TURNS}, {TOTAL_TURNS}, {TARGET_MONEY}, NOW())
    """)

    connection.commit()

    game_id = cursor.lastrowid

    connection.close()

    return game_id


def create_player(game_id):
    connection = get_connection()
    cursor = connection.cursor()

    name = input("Enter player name: ")

    cursor.execute(f"""
        INSERT INTO player
        (game_id, name, money, fuel, home_airport_ident, current_airport_ident)
        VALUES ({game_id}, '{name}', 1000, 600, 'EFHK', 'EFHK')
    """)

    connection.commit()

    player_id = cursor.lastrowid

    connection.close()

    print(f"\nWelcome aboard, Captain {name}!")

    return player_id

def get_fuel_price(airport_ident):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(f"""
        SELECT price_per_unit
        FROM fuel_price
        WHERE airport_ident = '{airport_ident}'
    """)

    result = cursor.fetchone()

    connection.close()

    return result[0]

def show_player(player_id, turns_left, message=None):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(f"""
        SELECT name, money, fuel, current_airport_ident
        FROM player
        WHERE id = {player_id}
    """)

    player = cursor.fetchone()

    fuel_price = get_fuel_price(player[3])

    location_name = "Helsinki" if player[3] == "EFHK" else player[3]

    fuel_bar = make_bar(player[2], MAX_FUEL)
    money_bar = make_bar(player[1], TARGET_MONEY)
    turns_bar = make_bar(turns_left, TOTAL_TURNS)

    print()
    print(f"Fuel   [{fuel_bar}] {player[2]} / {MAX_FUEL}")
    print(f"Money  [{money_bar}] {player[1]} / {TARGET_MONEY}€")
    print(f"Turns  [{turns_bar}] {turns_left} / {TOTAL_TURNS}")

    print()
    print(f"Current location: {location_name} | Fuel price: {fuel_price:.2f} €/unit")

    if message:
        print(f"\n{message}")

    connection.close()

    return player


def get_current_airport(player_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(f"""
        SELECT current_airport_ident
        FROM player
        WHERE id = {player_id}
    """)

    result = cursor.fetchone()

    connection.close()

    return result[0]

def get_airport_coordinates(ident):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(f"""
        SELECT latitude_deg, longitude_deg
        FROM airport
        WHERE ident = '{ident}'
    """)

    result = cursor.fetchone()

    connection.close()

    return result


def get_candidate_airports(current_airport_ident):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(f"""
            SELECT ident, municipality, latitude_deg, longitude_deg
            FROM airport
            WHERE ident != '{current_airport_ident}'
              AND municipality IS NOT NULL
              AND municipality != ''
              AND latitude_deg IS NOT NULL
              AND longitude_deg IS NOT NULL
              AND continent = 'EU'
              AND type IN ('medium_airport', 'large_airport')
        """)

    airports = cursor.fetchall()

    connection.close()

    return airports


def get_contracts(player_id):
    current_airport_ident = get_current_airport(player_id)
    current_coordinates = get_airport_coordinates(current_airport_ident)
    airports = get_candidate_airports(current_airport_ident)

    airport_distances = []

    for airport in airports:
        ident = airport[0]
        city = airport[1]
        latitude = airport[2]
        longitude = airport[3]

        distance = geodesic(
            (current_coordinates[0], current_coordinates[1]),
            (latitude, longitude)
        ).km

        airport_distances.append({
            "destination": ident,
            "destination_name": city,
            "distance": int(distance)
        })

    easy_airports = []
    medium_airports = []
    hard_airports = []

    for airport in airport_distances:

        if airport["distance"] < 1000:
            easy_airports.append(airport)

        elif airport["distance"] < 2500:
            medium_airports.append(airport)

        else:
            hard_airports.append(airport)

    if not easy_airports:
        easy_airports = airport_distances

    if not medium_airports:
        medium_airports = airport_distances

    if not hard_airports:
        hard_airports = airport_distances

    easy_airport = random.choice(easy_airports)
    medium_airport = random.choice(medium_airports)
    hard_airport = random.choice(hard_airports)

    selected_airports = [easy_airport, medium_airport, hard_airport]

    contracts = []

    for airport in selected_airports:
        fuel_needed = int(airport["distance"] * round(random.uniform(0.2, 0.25), 2))
        reward = int(airport["distance"] * round(random.uniform(0.45, 0.55), 2))

        contracts.append({
            "from": current_airport_ident,
            "destination": airport["destination"],
            "destination_name": airport["destination_name"],
            "distance": airport["distance"],
            "fuel_needed": fuel_needed,
            "reward": reward
        })

    return contracts

def refuel_player(game_id, player_id, fuel_amount):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(f"""
        SELECT money, fuel, current_airport_ident
        FROM player
        WHERE id = {player_id}
    """)

    player = cursor.fetchone()

    money = player[0]
    fuel = player[1]
    current_airport_ident = player[2]

    if fuel_amount <= 0:
        connection.close()
        return "Fuel amount must be greater than 0."

    if fuel >= MAX_FUEL:
        connection.close()
        return f"Fuel tank is already full. Maximum fuel is {MAX_FUEL}."

    if fuel + fuel_amount > MAX_FUEL:
        connection.close()
        return f"You cannot exceed the maximum fuel capacity of {MAX_FUEL}. You can only buy {MAX_FUEL - fuel} more fuel."

    fuel_price = get_fuel_price(current_airport_ident)
    total_cost = fuel_amount * fuel_price

    if money < total_cost:
        connection.close()
        return "Not enough money to buy that much fuel."

    cursor.execute(f"""
        UPDATE player
        SET
            money = money - {total_cost},
            fuel = fuel + {fuel_amount}
        WHERE id = {player_id}
    """)

    connection.commit()

    log_action(game_id, player_id, "REFUEL", fuel_bought=fuel_amount, fuel_price=fuel_price)

    connection.close()

    return f"Refueled {fuel_amount} units for {total_cost:.2f}€."

def choose_contract(game_id, player_id):
    message = None

    while True:
        clear_screen()
        turns_left = get_turns_left(game_id)
        show_player(player_id, turns_left, message)

        contracts = get_contracts(player_id)

        print("\nAvailable contracts:")
        print(f"1. {contracts[0]['destination_name']} | Distance {contracts[0]['distance']} km | Reward {contracts[0]['reward']}€ | Fuel needed {contracts[0]['fuel_needed']}")
        print(f"2. {contracts[1]['destination_name']} | Distance {contracts[1]['distance']} km | Reward {contracts[1]['reward']}€ | Fuel needed {contracts[1]['fuel_needed']}")
        print(f"3. {contracts[2]['destination_name']} | Distance {contracts[2]['distance']} km | Reward {contracts[2]['reward']}€ | Fuel needed {contracts[2]['fuel_needed']}")

        print("\nType 1, 2, 3 to take a contract")
        print(f"Type F amount to refuel (example: F 100, max fuel: {MAX_FUEL})")
        print("Type R to refresh player status")

        command = input("> ").upper().strip()
        message = None

        if command == "R":
            continue

        if command in ["1", "2", "3"]:
            selected_contract = contracts[int(command) - 1]

            connection = get_connection()
            cursor = connection.cursor()
            cursor.execute(f"""
                SELECT fuel
                FROM player
                WHERE id = {player_id}
            """)
            fuel = cursor.fetchone()[0]
            connection.close()

            if fuel < selected_contract["fuel_needed"]:
                message = "Not enough fuel for this flight."
                continue

            return selected_contract

        if command.startswith("F"):
            parts = command.split()

            if len(parts) == 2 and parts[1].isdigit():
                fuel_amount = int(parts[1])
                message = refuel_player(game_id, player_id, fuel_amount)
            else:
                message = "Invalid refuel command. Example: F 100"
            continue

        message = "Invalid command."


def log_action(game_id, player_id, action_type, contract=None, fuel_bought=None, fuel_price=None):

    connection = get_connection()
    cursor = connection.cursor()

    if action_type == "CONTRACT":

        cursor.execute(f"""
        INSERT INTO action_log
        (game_id, player_id, action_type, from_airport_ident, to_airport_ident,
         distance_km, fuel_used, money_change)
        VALUES (
            {game_id},
            {player_id},
            'CONTRACT',
            '{contract["from"]}',
            '{contract["destination"]}',
            {contract["distance"]},
            {contract["fuel_needed"]},
            {contract["reward"]}
        )
        """)

    if action_type == "REFUEL":

        cursor.execute(f"""
        INSERT INTO action_log
        (game_id, player_id, action_type, fuel_bought, fuel_price, refuel_cost)
        VALUES (
            {game_id},
            {player_id},
            'REFUEL',
            {fuel_bought},
            {fuel_price},
            {fuel_bought * fuel_price}
        )
        """)

    connection.commit()
    connection.close()

def update_player_after_contract(game_id, player_id, contract):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(f"""
        UPDATE player
        SET
            money = money + {contract['reward']},
            fuel = fuel - {contract['fuel_needed']},
            current_airport_ident = '{contract['destination']}'
        WHERE id = {player_id}
    """)

    connection.commit()

    log_action(game_id, player_id, "CONTRACT", contract=contract)

    connection.close()

    return f"Flight completed! You earned {contract['reward']}€ and used {contract['fuel_needed']} fuel."


def reduce_turn(game_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(f"""
        UPDATE game
        SET turns_left = turns_left - 1
        WHERE id = {game_id}
    """)

    connection.commit()
    connection.close()


def get_turns_left(game_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(f"""
        SELECT turns_left
        FROM game
        WHERE id = {game_id}
    """)

    result = cursor.fetchone()

    connection.close()

    return result[0]