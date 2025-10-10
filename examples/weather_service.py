import asyncio
import logging
from aiohttp import ClientSession
from init_provider import BaseProvider, requires

logging.basicConfig(level=logging.DEBUG, format="%(levelname)-8s %(message)s")

class GeoService(BaseProvider):
    def city_coordinates(self, name: str) -> tuple[float, float]:
        """Returns the latitude and longitude of a city."""
        if name == "London":
            return 51.509, -0.118  # London, UK
        elif name == "New York":
            return 40.7128, -74.0060  # New York, USA
        raise ValueError(f"Unknown city: {name}")

@requires(GeoService)
class WeatherService(BaseProvider):
    _session: ClientSession
    _base_url: str = "https://api.open-meteo.com/v1/forecast/"
    
    def provider_init(self) -> None:
        # Properly initializing aiohttp session at runtime, when the
        # default asyncio loop is already running.
        self._session = ClientSession(self._base_url)

    @classmethod
    async def close(cls):
        await cls._session.close()

    async def temperature(self, city: str) -> float:
        lat, lon = GeoService.city_coordinates(city)
        params = {"latitude": lat, "longitude": lon, "hourly": "temperature_2m"}
        async with self._session.get(self._base_url, params=params) as resp:
            data = await resp.json()
            return data["hourly"]["temperature_2m"][0]

async def main():
    # This will immediately initialize WeatherService and its dependencies,
    # because we have attempted to access the _session property.
    print(f"Is session closed: {WeatherService._session.closed}")

    # Subsequent calls do not reinitialize the provider.
    london = await WeatherService.temperature('London')
    new_york = await WeatherService.temperature('New York')
    print(f"London: {london:.2f}°C")
    print(f"New York: {new_york:.2f}°C")

    # Release the resources. Normally, this would be implemented in the
    # provider_dispose() method of the provider, but the async client must be closed
    # inside the same event loop it was created.
    await WeatherService.close()
    print(f"Is session closed: {WeatherService._session.closed}")


if __name__ == "__main__":
    asyncio.run(main())
