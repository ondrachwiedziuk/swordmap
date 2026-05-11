# Swordmap Game

Swordmap (KSP bojovka) is an interactive, location-based territorial control game where teams compete to capture and hold zones on a real-world map.

## Configuration

Edit `game_config.json` to define zones, bases, and their coordinates. Real-world coordinates (`latitude`, `longitude`) are now used instead of 2D coordinates:

```json
{
  "teams": [
    {
      "name": "TeamName",
      "color": "#FFFFFF"
    }
  ],
  "zones": [
    {
      "id": 1,
      "name": "Zone Name",
      "latitude": 50.087,
      "longitude": 14.421,
      "is_base": true,
      "owner": "TeamName",
      "color": "#FFFFFF",
      "adjacent_zones": [2, 3]
    }
  ]
}
```
- Teams are defined in the `teams` section of `game_config.json`. The `owner` field in the zones must match the name of a team defined there.
- Running `init_game_data` will apply these configurations and reset all team scores to 0.

## Setup (Docker)

The recommended way to run the application is via Docker Compose. Ensure your `.env` file is set up with PostgreSQL database credentials.

1. **Build and Run the Containers**:
    ```bash
    docker-compose up -d --build
    ```

2. **Initialize Database Data**:
    ```bash
    docker-compose exec web python manage.py migrate
    docker-compose exec web python manage.py init_game_data
    ```

*Note: The game loop for processing real-time game state (score increments & captures) is handled automatically by the `game_loop` container defined in `docker-compose.yml`.*

## Usage

- Navigate to `http://localhost:8000/`.
- Join a Team (or connect as an Admin).
- Check the **Pravidla** tab for complete game documentation and combat rules.
- View real-time scores in the **Statistiky** tab.
- Switch to the **Hra** tab, follow the OSM map using your live GPS location, and tap reachable nodes to capture them for your team!

