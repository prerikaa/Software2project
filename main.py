from db_initializer import initialize_database
from game_service import (
    initialize_fuel_prices,
    create_game,
    create_player,
    show_player,
    choose_contract,
    update_player_after_contract,
    reduce_turn,
    get_turns_left,
    clear_screen
)
from colorama import init, Fore
import time

init(autoreset=True)

def game_loop(game_id, player_id):
    while True:
        clear_screen()

        turns_left = get_turns_left(game_id)
        player = show_player(player_id, turns_left)

        money = player[1]
        fuel = player[2]

        if fuel < 0:
            print("\nYou lost! You ran out of fuel.")
            break

        if turns_left <= 0:
            print("\nYou lost! You ran out of turns.")
            break

        if money >= 3000:
            print("\nYou won! You reached the target profit.")
            break

        contract = choose_contract(game_id, player_id)

        update_message = update_player_after_contract(game_id, player_id, contract)
        reduce_turn(game_id)

        clear_screen()
        turns_left = get_turns_left(game_id)
        show_player(player_id, turns_left, update_message)

def start_game():
    print(Fore.CYAN + """
        ********************************************
        *                                          *
        *          Welcome to the Cargo Airline    *
        *              Simulation Game             *
        *                                          *
        ********************************************
        """)

    time.sleep(0.5)

    print(Fore.GREEN + "Welcome to the Cargo Airline Game!")
    time.sleep(0.3)

    print(Fore.YELLOW + "Your mission: Earn 3000€ before your turns run out.")
    print(Fore.RED + "Good luck, captain!")

    initialize_database()
    initialize_fuel_prices()

    game_id = create_game()
    player_id = create_player(game_id)

    game_loop(game_id, player_id)

start_game()