from flask import Flask, jsonify, request
from flask_cors import CORS
import game_service
from db_initializer import initialize_database

app = Flask(__name__)
CORS(app)

current_game_id = None
current_player_id = None
refresh_counter = 0


@app.route('/start', methods=['POST'])
def start_game():
    global current_game_id, current_player_id, refresh_counter
    try:
        data = request.json or {}
        pilot_name = data.get('name', 'Captain Anonymous') #gets pilot's name.

        initialize_database() #refreshes database
        game_service.initialize_fuel_prices() #gets fuel price

        current_game_id = game_service.create_game() #creates game entry

        current_player_id = game_service.create_player(current_game_id, pilot_name) # creates player

        refresh_counter = 0 #at the start of the game sets the counter at 0.

        return jsonify({
            "status": "success",
            "message": f"Welcome aboard, Captain {pilot_name}!",
            "player_id": current_player_id
        })
    except Exception as e:
        print(f"Error in /start: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/status', methods=['GET'])
def get_status():

    if not current_game_id or not current_player_id:
        return jsonify({"error": "No active game session found. Please start a new game."}), 400

    try:
        turns_left = game_service.get_turns_left(current_game_id)

        player = game_service.show_player(current_player_id, turns_left) # player structure: [name, money, fuel, current_airport_ident, city_name]. can be found in show_player function.

        ident = player[3]   # Extract location details ident = 4th column's value in the show_player data.
        city_name = player[4] # city_name is the fifth column's value.

        coords = game_service.get_airport_coordinates(ident)
        fuel_price = game_service.get_fuel_price(ident)

        contracts = game_service.get_contracts(current_player_id)

        return jsonify({
            "pilot": player[0],
            "money": player[1],
            "fuel": player[2],
            "turns": turns_left,
            "location": ident,
            "city": city_name,
            "fuel_price": fuel_price,
            "coords": {"lat": coords[0], "lng": coords[1]},
            "contracts": contracts,
            "max_fuel": game_service.MAX_FUEL,
            "goal_money": game_service.TARGET_MONEY
        })
    except Exception as e:
        print(f"Error in /status: {e}")
        return jsonify({"error": "Failed to retrieve game status"}), 500

@app.route('/fly', methods=['POST'])
def fly():
    try:
        data = request.json
        contract = data.get('contract')

        if not contract:
            return jsonify({"success": False, "message": "No contract selected."}), 400


        player = game_service.show_player(current_player_id, 0)
        if player[2] < contract['fuel_needed']:  # player[2] is the fuel level. check if the current fuel level is less than the fuel req.
            return jsonify({"success": False, "message": "Not enough fuel for this flight!"})
        msg = game_service.update_player_after_contract(current_game_id, current_player_id, contract)

        game_service.reduce_turn(current_game_id) #deduct a turn

        return jsonify({"success": True, "message": msg})
    except Exception as e:
        print(f"Error in /fly: {e}")
        return jsonify({"success": False, "message": "Flight system failure."}), 500




@app.route('/refuel', methods=['POST'])
def refuel():

    try:
        data = request.json
        try:
            amount = int(data.get('amount'))
        except (TypeError, ValueError):
            amount = 0

        if amount <= 0:
            return jsonify({"success": False, "message": "Please enter a positive fuel amount."})

        msg = game_service.refuel_player(current_game_id, current_player_id, amount)

        success = msg.startswith(
            "Refueled")  # if the return message after refuel_player function starts with Refueled.
        return jsonify({"success": success, "message": msg})

    except ValueError:
        return jsonify({"success": False, "message": "Invalid number format for fuel."})
    except Exception as e:
        print(f"Error in /refuel: {e}")
        return jsonify({"success": False, "message": "Refueling system offline."}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)