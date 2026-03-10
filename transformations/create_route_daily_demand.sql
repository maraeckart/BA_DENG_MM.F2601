CREATE TABLE route_daily_demand AS
SELECT
    start_station_id,
    start_station,
    end_station_id,
    end_station,
    trip_date,
    COUNT(*) AS trip_count,
    ROUND(AVG(duration_minutes), 2) AS avg_trip_duration
FROM bike_trips_clean
GROUP BY
    start_station_id,
    start_station,
    end_station_id,
    end_station,
    trip_date;