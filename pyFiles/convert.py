#Wana run without GUI? 
#Use "python3 -c 'from pyFiles.convert import convert; convert("/workspaces/DashCamDatToGPX/Testfiles/20251116.dat","/workspaces/DashCamDatToGPX/Testfiles/export.gpx")'"

import re
from datetime import datetime
from typing import Optional, Tuple, List, Dict

# Einfacher DAT->GPX Konverter
# Erwartet in .dat eine oder mehrere Zeilen mit Koordinaten (z.B. "52.5200,13.4050" oder "lat:52.5200 lon:13.4050").
# Schreibt eine minimale GPX-Datei mit einem Track und Trackpoints.
def _dms_to_decimal(deg: float, minutes: float = 0.0, seconds: float = 0.0, hemi: Optional[str] = None) -> float:
    dec = float(deg) + float(minutes) / 60.0 + float(seconds) / 3600.0
    if hemi and hemi.upper() in ("S", "W"):
        dec = -abs(dec)
    return dec

def _parse_dms(line: str) -> Optional[Tuple[float, float]]:
    # Beispiel: 52°30'0"N 13°24'0"E oder 52 30 0 N 13 24 0 E
    dms_re = re.compile(r"""
        (?P<deg>\d{1,3})\s*[°º]?\s*(?P<min>\d{1,2})?['’]?\s*(?P<sec>\d{1,2}(?:\.\d+)?)?["”]?\s*(?P<hemi>[NSEW])?
        """, re.VERBOSE | re.IGNORECASE)
    parts = list(dms_re.finditer(line))
    if len(parts) >= 2:
        latm = parts[0].groupdict()
        lonm = parts[1].groupdict()
        lat = _dms_to_decimal(latm.get('deg') or 0, latm.get('min') or 0, latm.get('sec') or 0, latm.get('hemi'))
        lon = _dms_to_decimal(lonm.get('deg') or 0, lonm.get('min') or 0, lonm.get('sec') or 0, lonm.get('hemi'))
        return lat, lon
    return None

def _parse_dashcam_csv(line: str) -> Optional[Dict]:
    # Beispiel-Format (Komma-getrennt): 20251116110416,50.336948,N,7.709287,E,0.000,182.991
    if not line or line.startswith('#'):
        return None
    parts = [p.strip() for p in line.split(',')]
    if len(parts) < 4:
        return None
    # Zeitstempel-Erkennung: 14-stellige Zeit (YYYYMMDDHHMMSS)
    ts = parts[0]
    if not re.fullmatch(r'\d{14}', ts):
        return None
    try:
        dt = datetime.strptime(ts, "%Y%m%d%H%M%S")
    except Exception:
        return None

    try:
        lat = float(parts[1])
        lat_dir = parts[2].upper() if len(parts) > 2 else ''
        if lat_dir == 'S':
            lat = -abs(lat)
        lon = float(parts[3])
        lon_dir = parts[4].upper() if len(parts) > 4 else ''
        if lon_dir == 'W':
            lon = -abs(lon)
    except Exception:
        return None

    speed = None
    if len(parts) > 5:
        try:
            speed = float(parts[5])
        except Exception:
            speed = None

    return {"lat": lat, "lon": lon, "time": dt.isoformat() + "Z", "speed": speed}

def _find_latlon_in_line(line: str) -> Optional[Tuple[float, float]]:
    # 1) Direktes "lat, lon" oder "lat;lon" oder "lat lon"
    m = re.search(r'([+-]?\d+(?:\.\d+)?)[,;\s]+([+-]?\d+(?:\.\d+)?)', line)
    if m:
        a, b = float(m.group(1)), float(m.group(2))
        # Heuristik: wenn erster Wert in Lat-Bereich und zweiter in Lon-Bereich => OK
        if -90 <= a <= 90 and -180 <= b <= 180:
            return a, b
        # Oder getauscht
        if -90 <= b <= 90 and -180 <= a <= 180:
            return b, a

    # 2) Schlüsselwort-Muster "lat:.. lon:.."
    m2 = re.search(r'lat[:=]\s*([+-]?\d+(?:\.\d+)?).*?lon[:=]\s*([+-]?\d+(?:\.\d+)?)', line, re.IGNORECASE)
    if m2:
        return float(m2.group(1)), float(m2.group(2))

    # 3) DMS oder mit Hemisphäre (N/S/E/W)
    dms = _parse_dms(line)
    if dms:
        return dms

    # 4) Fallback: finde alle Zahlen und wähle ein plausibles Paar
    nums = re.findall(r'[-+]?\d*\.\d+|[-+]?\d+', line)
    nums = [float(n) for n in nums]
    if len(nums) >= 2:
        # Suche aufeinander folgende Paare die in den lat/lon Bereich passen
        for i in range(len(nums) - 1):
            lat_candidate, lon_candidate = nums[i], nums[i+1]
            if -90 <= lat_candidate <= 90 and -180 <= lon_candidate <= 180:
                return lat_candidate, lon_candidate
            if -90 <= lon_candidate <= 90 and -180 <= lat_candidate <= 180:
                # Wenn Reihenfolge verdreht, drehe
                return lon_candidate, lat_candidate

    return None

def convert(dat_path: str, out_path: str):
    coords: List[Dict] = []
    with open(dat_path, "r", encoding="utf-8", errors="ignore") as fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            # 1) Versuch: DashCam CSV spez. Format
            entry = _parse_dashcam_csv(line)
            if entry:
                coords.append(entry)
                continue
            # 2) Versuch: allgemeines lat/lon parsing
            match = _find_latlon_in_line(line)
            if match:
                # fallback ohne zeit/speed
                lat, lon = match
                coords.append({"lat": lat, "lon": lon, "time": None, "speed": None})

    if not coords:
        raise ValueError("Keine Koordinaten in der DAT-Datei gefunden.")

    # Minimaler GPX-Aufbau mit gpxtpx Namespace für speed
    header = '<?xml version="1.0" encoding="UTF-8"?>\n'
    header += '<gpx version="1.1" creator="DashCamDatToGPX" '
    header += 'xmlns:gpxtpx="http://www.garmin.com/xmlschemas/TrackPointExtension/v1">\n'
    header += '  <trk>\n'
    header += '    <name>Converted from DAT</name>\n'
    header += '    <trkseg>\n'

    trkpts = []
    for p in coords:
        lat = p["lat"]
        lon = p["lon"]
        trk = f'      <trkpt lat="{lat:.6f}" lon="{lon:.6f}">\n'
        if p.get("time"):
            trk += f'        <time>{p["time"]}</time>\n'
        # speed optional in gpxtpx extension
        if p.get("speed") is not None:
            trk += '        <extensions>\n'
            trk += '          <gpxtpx:TrackPointExtension>\n'
            trk += f'            <gpxtpx:speed>{p["speed"]:.3f}</gpxtpx:speed>\n'
            trk += '          </gpxtpx:TrackPointExtension>\n'
            trk += '        </extensions>\n'
        trk += '      </trkpt>\n'
        trkpts.append(trk)

    footer = '    </trkseg>\n'
    footer += '  </trk>\n'
    footer += '</gpx>\n'

    with open(out_path, "w", encoding="utf-8") as out_fh:
        out_fh.write(header)
        out_fh.writelines(trkpts)
        out_fh.write(footer)
