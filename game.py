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


if __name__ == '_main_':
    app.run(debug=True, port=5000)