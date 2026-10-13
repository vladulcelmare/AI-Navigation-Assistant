class TripCreationError(Exception):
    pass

class VehicleNotFoundError(TripCreationError):
    pass

class VehicleOwnershipError(TripCreationError):
    pass

class VehicleUnavailableError(TripCreationError):
    pass

class InfeasibleRouteError(TripCreationError):
    pass

class RouteServiceError(TripCreationError):
    pass

class GeoapifyError(RuntimeError):
    """Raised when Geoapify cannot provide a usable response."""
    pass
