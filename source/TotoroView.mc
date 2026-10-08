import Toybox.Graphics;
import Toybox.Lang;
import Toybox.System;
import Toybox.Time;
import Toybox.Time.Gregorian;
import Toybox.WatchUi;

// Couleurs relevées sur la maquette ; les positions viennent de layout.json.
const CREAM = 0xF6E6CC;
const AOD_TIME_COLOR = 0x8C8272;

const DAYS = ["DIM", "LUN", "MAR", "MER", "JEU", "VEN", "SAM"];
const MONTHS = ["JAN", "FEV", "MAR", "AVR", "MAI", "JUIN", "JUIL", "AOUT", "SEPT", "OCT", "NOV", "DEC"];

// Icônes jour pour chaque WeatherKind, puis variantes de nuit (ciel dégagé, éclaircies).
const WEATHER_ICONS = [
    Rez.Drawables.WeatherClear,
    Rez.Drawables.WeatherPartly,
    Rez.Drawables.WeatherCloudy,
    Rez.Drawables.WeatherRain,
    Rez.Drawables.WeatherSnow,
    Rez.Drawables.WeatherStorm,
    Rez.Drawables.WeatherFog,
];
const NIGHT_START_HOUR = 20;
const NIGHT_END_HOUR = 7;

class TotoroView extends WatchUi.WatchFace {

    private var _data as DataProvider;
    private var _layout as Dictionary;
    private var _timeFont as FontResource;
    private var _dateFont as FontResource;
    private var _bg as BitmapResource?;
    private var _bgAod as BitmapResource?;
    private var _weatherIcon as BitmapResource?;
    private var _weatherIconId as ResourceId?;
    private var _isSleeping as Boolean = false;

    function initialize() {
        WatchFace.initialize();
        _data = new DataProvider();
        _layout = WatchUi.loadResource(Rez.JsonData.Layout) as Dictionary;
        _timeFont = WatchUi.loadResource(Rez.Fonts.TimeFont) as FontResource;
        _dateFont = WatchUi.loadResource(Rez.Fonts.DateFont) as FontResource;
    }

    function onLayout(dc as Dc) as Void {
        _bg = WatchUi.loadResource(Rez.Drawables.BgScene) as BitmapResource;
    }

    function onUpdate(dc as Dc) as Void {
        if (dc has :setAntiAlias) {
            dc.setAntiAlias(true);
        }
        if (_isSleeping) {
            drawAlwaysOn(dc);
        } else {
            drawActive(dc);
        }
    }

    // Mode basse consommation : on ne garde qu'une image de fond en mémoire.
    function onEnterSleep() as Void {
        _isSleeping = true;
        _bg = null;
        _bgAod = WatchUi.loadResource(Rez.Drawables.BgAod) as BitmapResource;
        WatchUi.requestUpdate();
    }

    function onExitSleep() as Void {
        _isSleeping = false;
        _bgAod = null;
        _bg = WatchUi.loadResource(Rez.Drawables.BgScene) as BitmapResource;
        WatchUi.requestUpdate();
    }

    private function drawActive(dc as Dc) as Void {
        if (_bg != null) {
            dc.drawBitmap(0, 0, _bg);
        }

        var time = _layout["time"] as Array<Number>;
        dc.setColor(CREAM, Graphics.COLOR_TRANSPARENT);
        dc.drawText(time[0], time[1], _timeFont, getTimeString(), Graphics.TEXT_JUSTIFY_CENTER | Graphics.TEXT_JUSTIFY_VCENTER);

        // Date centrée dans sa zone. Haut du texte calculé ici plutôt qu'avec
        // TEXT_JUSTIFY_VCENTER, qui décalait le texte d'un pixel vers le bas : la boîte des
        // polices fait exactement les capitales plus une marge égale (tools/make_fonts.py).
        var date = _layout["dateArea"] as Array<Number>;
        dc.drawText(date[0] + date[2] / 2, date[1] + date[3] / 2 - dc.getFontHeight(_dateFont) / 2,
            _dateFont, getDateString(), Graphics.TEXT_JUSTIFY_CENTER);

        // Météo au milieu du ventre de Totoro.
        var weatherIcon = getWeatherIcon();
        if (weatherIcon != null) {
            var w = _layout["weather"] as Array<Number>;
            dc.drawBitmap(w[0] - weatherIcon.getWidth() / 2, w[1] - weatherIcon.getHeight() / 2, weatherIcon);
        }
    }

    private function getWeatherIcon() as BitmapResource? {
        var kind = _data.getWeatherKind();
        if (kind == null) {
            return null;
        }
        var id = WEATHER_ICONS[kind] as ResourceId;
        var hour = System.getClockTime().hour;
        if (hour >= NIGHT_START_HOUR || hour < NIGHT_END_HOUR) {
            if (kind == WEATHER_CLEAR) {
                id = Rez.Drawables.WeatherNight;
            } else if (kind == WEATHER_PARTLY) {
                id = Rez.Drawables.WeatherPartlyNight;
            }
        }
        // Une seule icône en mémoire, rechargée seulement quand la météo change.
        if (id != _weatherIconId) {
            _weatherIcon = WatchUi.loadResource(id) as BitmapResource;
            _weatherIconId = id;
        }
        return _weatherIcon;
    }

    // AMOLED : contours de la scène et heure seule, légèrement décalée chaque minute
    // pour éviter le marquage de l'écran.
    private function drawAlwaysOn(dc as Dc) as Void {
        dc.setColor(Graphics.COLOR_BLACK, Graphics.COLOR_BLACK);
        dc.clear();
        if (_bgAod != null) {
            dc.drawBitmap(0, 0, _bgAod);
        }
        var min = System.getClockTime().min;
        var dx = (min % 5 - 2) * 3;
        var dy = ((min / 5) % 5 - 2) * 3;
        var time = _layout["time"] as Array<Number>;
        dc.setColor(AOD_TIME_COLOR, Graphics.COLOR_TRANSPARENT);
        dc.drawText(time[0] + dx, time[1] + dy, _timeFont, getTimeString(),
            Graphics.TEXT_JUSTIFY_CENTER | Graphics.TEXT_JUSTIFY_VCENTER);
    }

    private function getTimeString() as String {
        var clock = System.getClockTime();
        var hour = clock.hour;
        var hourFormat = "%02d";
        if (!System.getDeviceSettings().is24Hour) {
            hour = hour % 12;
            if (hour == 0) {
                hour = 12;
            }
            hourFormat = "%d";
        }
        return Lang.format("$1$:$2$", [hour.format(hourFormat), clock.min.format("%02d")]);
    }

    // Date en français et en capitales, ex. "JEU 8 OCT".
    private function getDateString() as String {
        var info = Gregorian.info(Time.now(), Time.FORMAT_SHORT);
        var day = DAYS[(info.day_of_week as Number) - 1];
        var month = MONTHS[(info.month as Number) - 1];
        return Lang.format("$1$ $2$ $3$", [day, info.day, month]);
    }
}
