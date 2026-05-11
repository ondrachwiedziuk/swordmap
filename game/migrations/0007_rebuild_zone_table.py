from django.db import migrations


def rebuild_zone_table_if_legacy(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        columns = {
            row[1] for row in cursor.execute("PRAGMA table_info(game_zone)").fetchall()
        }

        # Only rebuild when legacy coordinate columns are still present.
        if "x_coordinate" not in columns and "y_coordinate" not in columns:
            return

        cursor.execute("PRAGMA foreign_keys=OFF")

        cursor.execute(
            """
            CREATE TABLE game_zone_new (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                longitude REAL NOT NULL DEFAULT 0.0,
                latitude REAL NOT NULL DEFAULT 0.0,
                is_base BOOL NOT NULL DEFAULT 0,
                default_color VARCHAR(20) NOT NULL DEFAULT '#FFFFFF',
                status VARCHAR(20) NOT NULL DEFAULT 'NEUTRAL',
                capture_started_at DATETIME NULL,
                last_score_update DATETIME NULL,
                capturing_team_id INTEGER NULL REFERENCES game_team(id) DEFERRABLE INITIALLY DEFERRED,
                owner_id INTEGER NULL REFERENCES game_team(id) DEFERRABLE INITIALLY DEFERRED
            )
            """
        )

        cursor.execute(
            """
            INSERT INTO game_zone_new (
                id,
                name,
                longitude,
                latitude,
                is_base,
                default_color,
                status,
                capture_started_at,
                last_score_update,
                capturing_team_id,
                owner_id
            )
            SELECT
                id,
                name,
                COALESCE(longitude, x_coordinate, 0.0),
                COALESCE(latitude, y_coordinate, 0.0),
                COALESCE(is_base, 0),
                COALESCE(default_color, '#FFFFFF'),
                COALESCE(status, 'NEUTRAL'),
                capture_started_at,
                last_score_update,
                capturing_team_id,
                owner_id
            FROM game_zone
            """
        )

        cursor.execute("DROP TABLE game_zone")
        cursor.execute("ALTER TABLE game_zone_new RENAME TO game_zone")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS game_zone_capturing_team_id_idx ON game_zone(capturing_team_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS game_zone_owner_id_idx ON game_zone(owner_id)"
        )

        cursor.execute("PRAGMA foreign_keys=ON")


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("game", "0006_alter_team_color"),
    ]

    operations = [
        migrations.RunPython(rebuild_zone_table_if_legacy, migrations.RunPython.noop),
    ]
