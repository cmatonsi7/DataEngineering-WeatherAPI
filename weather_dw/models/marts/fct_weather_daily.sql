-- ── WHAT IS THIS MODEL? ────────────────────────────────────────────────────────
-- Fact table for daily weather per city.
-- This is the final table analysts and dashboards query.
-- One row per city per day.
-- ───────────────────────────────────────────────────────────────────────────────

WITH staging AS (
    SELECT * FROM {{ ref('stg_weather') }}
),

final AS (
    SELECT
        -- Natural key: city + date uniquely identifies each row
        city,
        date,

        -- Location
        latitude,
        longitude,

        -- Temperature metrics
        temp_max,
        temp_min,
        temp_mean,
        temp_range,

        -- Precipitation
        precipitation_mm,
        had_precipitation,

        -- Wind
        windspeed_max,

        -- Weather classification
        weather_code,
        weather_description,

        -- Metadata
        extracted_at
    FROM staging
)

SELECT * FROM final
ORDER BY date DESC, city ASC