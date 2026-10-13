USE In_Car_Assistant_DB;
GO

IF COL_LENGTH('Users_Trips.history', 'route_json') IS NULL
BEGIN
    ALTER TABLE Users_Trips.history
    ADD route_json nvarchar(max) NULL;
END;
GO

IF COL_LENGTH('Users_Trips.history', 'trip_status') IS NULL
BEGIN
    ALTER TABLE Users_Trips.history
    ADD trip_status varchar(20) NOT NULL
        CONSTRAINT DF_trip_history_status DEFAULT 'COMPLETED'
        CONSTRAINT CK_trip_history_status CHECK (
            trip_status IN ('PLANNED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')
        );
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_trip_history_active_vehicle'
      AND object_id = OBJECT_ID('Users_Trips.history')
)
BEGIN
    CREATE INDEX IX_trip_history_active_vehicle
        ON Users_Trips.history (vehicle_id, trip_status);
END;
GO