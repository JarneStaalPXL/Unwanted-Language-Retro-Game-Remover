import os
import requests
import curses
import time
import statistics

CHECKED_GAMES_FILE = "checked_games.txt"

def load_checked_games():
    if os.path.exists(CHECKED_GAMES_FILE):
        with open(CHECKED_GAMES_FILE, "r") as file:
            return set(file.read().splitlines())
    return set()

def save_checked_game(filename):
    with open(CHECKED_GAMES_FILE, "a") as file:
        file.write(f"{filename}\n")

def is_game_language(filename, keep_languages, retries=5, delay=10):
    payload = {
        "model": "searchgpt",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant. "
                    "Determine if the filename suggests a Japanese, Chinese, or English game. "
                    "If the filename suggests Japanese or Chinese, respond with 'Japanese' or 'Chinese'. "
                    "If it's English, respond with 'English'. Only answer one word."
                )
            },
            {
                "role": "user",
                "content": f"Filename: {filename}"
            }
        ]
    }

    for attempt in range(1, retries + 1):
        try:
            response = requests.post(
                "https://text.pollinations.ai/",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=50
            )
            response.raise_for_status()
            answer_text = response.text.strip().lower()
            print(f"[INFO] Pollinations response for '{filename}': {answer_text}")
            return answer_text in keep_languages
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Attempt {attempt}/{retries} failed for '{filename}': {e}")
            if attempt < retries:
                print(f"[INFO] Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print(f"[ERROR] All attempts failed for '{filename}'. Skipping this file.")
                return False

def curses_menu(stdscr, options):
    curses.curs_set(0)  # Disable cursor
    selected = [False] * len(options)
    current_row = 0

    while True:
        stdscr.clear()
        stdscr.addstr("Select languages to keep (Press SPACE to select, ENTER to confirm):\n\n")

        for idx, option in enumerate(options):
            marker = "*" if selected[idx] else " "
            if idx == current_row:
                stdscr.addstr(f"> {marker} {option}\n", curses.color_pair(1))
            else:
                stdscr.addstr(f"  {marker} {option}\n")

        key = stdscr.getch()

        if key == curses.KEY_UP and current_row > 0:
            current_row -= 1
        elif key == curses.KEY_DOWN and current_row < len(options) - 1:
            current_row += 1
        elif key == ord(" "):  # Toggle selection
            selected[current_row] = not selected[current_row]
        elif key == ord("\n"):  # Confirm selection
            break

    return [options[idx].lower() for idx, is_selected in enumerate(selected) if is_selected]

def select_languages():
    options = ["English", "Japanese", "Chinese"]
    return curses.wrapper(curses_menu, options)

def format_time(seconds):
    """Formats time in seconds to a readable string."""
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 0:
        return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
    elif minutes > 0:
        return f"{int(minutes)}m {int(seconds)}s"
    else:
        return f"{int(seconds)}s"

def main():
    keep_languages = select_languages()
    if not keep_languages:
        print("No languages selected. Exiting...")
        return

    print(f"Selected languages to keep: {', '.join(keep_languages)}")
    checked_games = load_checked_games()

    zip_files = []
    for root, dirs, files in os.walk('.'):
        for file_name in files:
            if file_name.lower().endswith('.zip'):
                full_path = os.path.join(root, file_name)
                zip_files.append(full_path)

    total_games = len(zip_files)
    print(f"Total games found: {total_games}")
    remaining_games = total_games - len(checked_games)

    time_per_game = []
    for idx, zip_path in enumerate(zip_files):
        if zip_path in checked_games:
            print(f"[SKIPPING] Already checked -> {zip_path}")
            continue

        start_time = time.time()
        print(f"[INFO] Processing game {idx + 1}/{total_games}. Remaining: {remaining_games}")

        if is_game_language(zip_path, keep_languages):
            print(f"[KEEPING] Game in selected language -> {zip_path}")
        else:
            print(f"[REMOVING] Game not in selected language -> {zip_path}")
            os.remove(zip_path)

        elapsed_time = time.time() - start_time
        time_per_game.append(elapsed_time)

        if time_per_game:
            average_time = statistics.mean(time_per_game)
            estimated_time_left = average_time * (remaining_games - 1)
            print(f"[INFO] Estimated time left: {format_time(estimated_time_left)}")

        save_checked_game(zip_path)
        remaining_games -= 1

if __name__ == "__main__":
    main()
