CREATE TABLE bike_trips_clean AS
SELECT
    "Number" AS trip_id,
    "Start date" AS start_time,
    "End date" AS end_time,
    "Start station number" AS start_station_id,
    "Start station" AS start_station,
    "End station number" AS end_station_id,
    "End station" AS end_station,
    "Bike number" AS bike_id,
    "Bike model" AS bike_model,
    "Total duration (ms)" AS duration_ms,
    ROUND(("Total duration (ms)" / 60000.0),2) AS duration_minutes,
    DATE("Start date") AS trip_date,
    EXTRACT(HOUR FROM "Start date") AS hour_of_day,
    EXTRACT(DOW FROM "Start date") AS day_of_week,
    CASE
        WHEN EXTRACT(DOW FROM "Start date") IN (0,6)
        THEN 1 ELSE 0
    END AS is_weekend
FROM london_bike_data;