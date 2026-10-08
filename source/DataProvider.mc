import Toybox.Lang;
import Toybox.System;
import Toybox.Weather;

// Familles de conditions météo, une icône par famille.
enum WeatherKind {
    WEATHER_CLEAR,
    WEATHER_PARTLY,
    WEATHER_CLOUDY,
    WEATHER_RAIN,
    WEATHER_SNOW,
    WEATHER_STORM,
    WEATHER_FOG,
}

// Lecture des données affichées par le cadran : batterie et météo (null si indisponible).
class DataProvider {

    function initialize() {
    }

    function getBattery() as Number {
        return System.getSystemStats().battery.toNumber();
    }

    // Conditions actuelles, synchronisées depuis le téléphone par Garmin Connect.
    function getWeatherKind() as WeatherKind? {
        if (!(Toybox has :Weather)) {
            return null;
        }
        var conditions = Weather.getCurrentConditions();
        var condition = conditions != null ? conditions.condition : null;
        if (condition == null) {
            return null;
        }
        switch (condition) {
            case Weather.CONDITION_CLEAR:
            case Weather.CONDITION_MOSTLY_CLEAR:
            case Weather.CONDITION_FAIR:
                return WEATHER_CLEAR;
            case Weather.CONDITION_PARTLY_CLOUDY:
            case Weather.CONDITION_PARTLY_CLEAR:
            case Weather.CONDITION_THIN_CLOUDS:
                return WEATHER_PARTLY;
            case Weather.CONDITION_MOSTLY_CLOUDY:
            case Weather.CONDITION_CLOUDY:
            case Weather.CONDITION_WINDY:
                return WEATHER_CLOUDY;
            case Weather.CONDITION_RAIN:
            case Weather.CONDITION_SCATTERED_SHOWERS:
            case Weather.CONDITION_UNKNOWN_PRECIPITATION:
            case Weather.CONDITION_LIGHT_RAIN:
            case Weather.CONDITION_HEAVY_RAIN:
            case Weather.CONDITION_LIGHT_SHOWERS:
            case Weather.CONDITION_SHOWERS:
            case Weather.CONDITION_HEAVY_SHOWERS:
            case Weather.CONDITION_CHANCE_OF_SHOWERS:
            case Weather.CONDITION_DRIZZLE:
            case Weather.CONDITION_CLOUDY_CHANCE_OF_RAIN:
            case Weather.CONDITION_FREEZING_RAIN:
                return WEATHER_RAIN;
            case Weather.CONDITION_SNOW:
            case Weather.CONDITION_WINTRY_MIX:
            case Weather.CONDITION_HAIL:
            case Weather.CONDITION_LIGHT_SNOW:
            case Weather.CONDITION_HEAVY_SNOW:
            case Weather.CONDITION_LIGHT_RAIN_SNOW:
            case Weather.CONDITION_HEAVY_RAIN_SNOW:
            case Weather.CONDITION_RAIN_SNOW:
            case Weather.CONDITION_ICE:
            case Weather.CONDITION_CHANCE_OF_SNOW:
            case Weather.CONDITION_CHANCE_OF_RAIN_SNOW:
            case Weather.CONDITION_CLOUDY_CHANCE_OF_SNOW:
            case Weather.CONDITION_CLOUDY_CHANCE_OF_RAIN_SNOW:
            case Weather.CONDITION_FLURRIES:
            case Weather.CONDITION_SLEET:
            case Weather.CONDITION_ICE_SNOW:
                return WEATHER_SNOW;
            case Weather.CONDITION_THUNDERSTORMS:
            case Weather.CONDITION_SCATTERED_THUNDERSTORMS:
            case Weather.CONDITION_CHANCE_OF_THUNDERSTORMS:
            case Weather.CONDITION_TORNADO:
            case Weather.CONDITION_HURRICANE:
            case Weather.CONDITION_TROPICAL_STORM:
            case Weather.CONDITION_SQUALL:
                return WEATHER_STORM;
            case Weather.CONDITION_FOG:
            case Weather.CONDITION_HAZY:
            case Weather.CONDITION_MIST:
            case Weather.CONDITION_DUST:
            case Weather.CONDITION_SMOKE:
            case Weather.CONDITION_SAND:
            case Weather.CONDITION_SANDSTORM:
            case Weather.CONDITION_VOLCANIC_ASH:
            case Weather.CONDITION_HAZE:
                return WEATHER_FOG;
        }
        return null;
    }
}
