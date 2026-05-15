import pandas as pd


def parse_feed(raw_json: dict) -> pd.DataFrame:
    """Parse NeoWs feed JSON into a clean DataFrame."""
    rows = []
    for date_str, neos in raw_json.get("near_earth_objects", {}).items():
        for neo in neos:
            cad = neo.get("close_approach_data", [{}])[0]
            diam = neo.get("estimated_diameter", {}).get("kilometers", {})
            diam_min = diam.get("estimated_diameter_min", 0)
            diam_max = diam.get("estimated_diameter_max", 0)
            rows.append({
                "name": neo.get("name", ""),
                "date": pd.to_datetime(date_str),
                "diameter_km": (diam_min + diam_max) / 2,
                "velocity_kms": float(
                    cad.get("relative_velocity", {})
                       .get("kilometers_per_second", 0)
                ),
                "miss_distance_au": float(
                    cad.get("miss_distance", {}).get("astronomical", 0)
                ),
                "miss_distance_ld": float(
                    cad.get("miss_distance", {}).get("lunar", 0)
                ),
                "is_hazardous": neo.get(
                    "is_potentially_hazardous_asteroid", False
                ),
                "magnitude": neo.get("absolute_magnitude_h", None),
            })

    df = pd.DataFrame(rows)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
    return df


def parse_browse(raw_json: dict) -> pd.DataFrame:
    """Parse NeoWs browse JSON, adding orbit_class column."""
    rows = []
    for neo in raw_json.get("near_earth_objects", []):
        cad_list = neo.get("close_approach_data", [{}])
        cad = cad_list[0] if cad_list else {}
        diam = neo.get("estimated_diameter", {}).get("kilometers", {})
        diam_min = diam.get("estimated_diameter_min", 0)
        diam_max = diam.get("estimated_diameter_max", 0)
        orbit_data = neo.get("orbital_data", {})
        orbit_class = (
            orbit_data.get("orbit_class", {}).get("orbit_class_type", "Unknown")
        )
        rows.append({
            "name": neo.get("name", ""),
            "diameter_km": (diam_min + diam_max) / 2,
            "velocity_kms": float(
                cad.get("relative_velocity", {})
                   .get("kilometers_per_second", 0)
            ),
            "miss_distance_au": float(
                cad.get("miss_distance", {}).get("astronomical", 0)
            ),
            "miss_distance_ld": float(
                cad.get("miss_distance", {}).get("lunar", 0)
            ),
            "is_hazardous": neo.get(
                "is_potentially_hazardous_asteroid", False
            ),
            "magnitude": neo.get("absolute_magnitude_h", None),
            "orbit_class": orbit_class,
        })

    return pd.DataFrame(rows)


def merge_historical_feeds(raw_list: list[dict]) -> pd.DataFrame:
    """Merge a list of raw feed JSONs into one DataFrame."""
    frames = [parse_feed(raw) for raw in raw_list]
    frames = [f for f in frames if not f.empty]
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    df = df.drop_duplicates(subset=["name", "date"]).reset_index(drop=True)
    return df
