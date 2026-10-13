USE In_Car_Assistant_DB;
GO

IF COL_LENGTH('Users_Vehicles.vehicle', 'current_location_json') IS NULL
    ALTER TABLE Users_Vehicles.vehicle ADD current_location_json nvarchar(max) NULL;
GO

IF COL_LENGTH('Users_Chats.Conversations', 'recommendations_json') IS NULL
    ALTER TABLE Users_Chats.Conversations ADD recommendations_json nvarchar(max) NULL;
GO
