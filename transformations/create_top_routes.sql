DROP TABLE IF EXISTS top_routes;

CREATE TABLE top_routes AS
SELECT
    start_station_id,
    start_station,
    end_station_id,
    end_station,
    COUNT(*) AS trip_count
FROM bike_trips_clean
GROUP BY
    start_station_id,
    start_station,
    end_station_id,
    end_station
ORDER BY trip_count DESC
LIMIT 50;