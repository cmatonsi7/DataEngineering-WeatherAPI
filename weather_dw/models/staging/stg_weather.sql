-- ── WHAT IS THIS MODEL? ────────────────────────────────────────────────────────
-- Staging model for daily weather data.
-- Reads from raw.weather_daily loaded by our transform script.
-- Adds a human-readable weather description based on the WMO weather code,
-- and a derived column indicating whether it rained that day.
--
-- WMO weather codes are a standard system:
-- 0 = Clear sky, 1-3 = Partly cloudy, 45-48 = Fog,
-- 51-67 = Rain, 71-77 = Snow, 80-82 = Rain showers, 95+ = Thunderstorm
-- ───────────────────────────────────────────────────────────────────────────────

WITH source AS (
    SELECT * FROM raw.weather_daily
),

cleaned AS (
    SELECT
        city,
        date,
        latitude,
        longitude,
        timezone,
        temp_max,
        temp_min,
        temp_mean,
        precipitation_mm,
        windspeed_max,
        weather_code,

        -- Derived: temperature range for the day
        ROUND(temp_max - temp_min, 1)       AS temp_range,

        -- Derived: did it rain today?
        CASE
            WHEN precipitation_mm > 0 THEN TRUE
            ELSE FALSE
        END                                 AS had_precipitation,

        -- Derived: human readable weather description from WMO code
        CASE
            WHEN weather_code = 0  THEN 'Clear Sky'
            WHEN weather_code IN (1, 2, 3) THEN 'Partly Cloudy'
            WHEN weather_code IN (45, 48) THEN 'Fog'
            WHEN weather_code BETWEEN 51 AND 67 THEN 'Rain'
            WHEN weather_code BETWEEN 71 AND 77 THEN 'Snow'
            WHEN weather_code BETWEEN 80 AND 82 THEN 'Rain Showers'
            WHEN weather_code >= 95 THEN 'Thunderstorm'
            ELSE 'Unknown'
        END                                 AS weather_description,

        extracted_at

    FROM source
    WHERE city IS NOT NULL
      AND date IS NOT NULL
)

SELECT * FROM cleaned