DROP TABLE IF EXISTS station_hourly_demand;

CREATE TABLE station_hourly_demand AS
SELECT
    start_station_id,
    start_station,
    trip_date,
    hour_of_day,
    COUNT(*) AS trip_count,
    ROUND(AVG(duration_minutes),2) AS avg_trip_duration
FROM bike_trips_clean
GROUP BY
    start_station_id,
    start_station,
    trip_date,
    hour_of_day;
