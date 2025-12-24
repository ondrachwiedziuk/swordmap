# Swordmap Game

## Setup

1.  **Install Dependencies**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

2.  **Database Configuration**:
    -   Ensure you have MariaDB installed and running.
    -   Create a database named `swordmap`.
    -   Update `.env` file with your database credentials.

3.  **Configuration**:
    -   Edit `game_config.json` to define zones, bases, and their coordinates.
    -   Place your map image at `game/static/game/map.png` (already done if you followed instructions).

4.  **Initialize Database**:
    ```bash
    python manage.py migrate
    python manage.py init_game_data
    ```

5.  **Run Server**:
    ```bash
    python manage.py runserver
    ```

5.  **Game Loop**:
    To process captures and scores, you need to run the following command periodically (e.g., every 10 seconds) or in a loop:
    ```bash
    python manage.py process_game_state
    ```

## Usage

-   Go to `http://localhost:8000/`
-   Choose your role (Admin, Yellow, Blue, Black).
-   Click on zones to capture/defend.
