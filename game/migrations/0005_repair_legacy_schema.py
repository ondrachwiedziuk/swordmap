from django.db import migrations


def repair_legacy_schema(apps, schema_editor):
    """Repair SQLite schema drift when early migrations were edited after apply."""

    def get_columns(cursor, table_name):
        rows = cursor.execute(f"PRAGMA table_info({table_name})").fetchall()
        return {row[1] for row in rows}

    with schema_editor.connection.cursor() as cursor:
        game_columns = get_columns(cursor, "game_game")
        missing_game_columns = [
            ("mode", "TEXT NOT NULL DEFAULT 'STANDARD'"),
            ("accepted_distance", "REAL NOT NULL DEFAULT 5"),
            ("top_left_longitude", "REAL NOT NULL DEFAULT 0.0"),
            ("top_left_latitude", "REAL NOT NULL DEFAULT 0.0"),
            ("bottom_right_longitude", "REAL NOT NULL DEFAULT 0.0"),
            ("bottom_right_latitude", "REAL NOT NULL DEFAULT 0.0"),
        ]

        for column_name, column_definition in missing_game_columns:
            if column_name not in game_columns:
                cursor.execute(
                    f"ALTER TABLE game_game ADD COLUMN {column_name} {column_definition}"
                )

        zone_columns = get_columns(cursor, "game_zone")
        if "longitude" not in zone_columns:
            cursor.execute(
                "ALTER TABLE game_zone ADD COLUMN longitude REAL NOT NULL DEFAULT 0.0"
            )
        if "latitude" not in zone_columns:
            cursor.execute(
                "ALTER TABLE game_zone ADD COLUMN latitude REAL NOT NULL DEFAULT 0.0"
            )

        zone_columns = get_columns(cursor, "game_zone")
        if "x_coordinate" in zone_columns and "longitude" in zone_columns:
            cursor.execute(
                "UPDATE game_zone SET longitude = x_coordinate WHERE x_coordinate IS NOT NULL"
            )
        if "y_coordinate" in zone_columns and "latitude" in zone_columns:
            cursor.execute(
                "UPDATE game_zone SET latitude = y_coordinate WHERE y_coordinate IS NOT NULL"
            )


class Migration(migrations.Migration):

    dependencies = [
        ("game", "0004_alter_team_color"),
    ]

    operations = [
        migrations.RunPython(repair_legacy_schema, migrations.RunPython.noop),
    ]
