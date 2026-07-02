// SatelliteGlobe — real-time satellite display for VRChat worlds.
//
// Downloads data/orbits.csv from this repository, then propagates every
// satellite with the Kepler + secular-J2 model (the reference
// implementation, with tests, lives in satglobe/kepler.py — keep the
// math identical). Because propagation runs locally, positions stay
// smooth and current even though the data file only refreshes every
// 10 minutes.
//
// Setup:
//   1. Create a globe sphere; note its radius in world units.
//   2. Add a ParticleSystem as a child (see clients/vrchat/README.md
//      for the required module settings).
//   3. Attach this UdonSharp behaviour, assign the fields, and set
//      Orbits Url to:
//      https://raw.githubusercontent.com/010kumaguma010/satellite-globe/main/data/orbits.csv
//
// Both parsing and per-frame updates are sliced across frames so a
// ~13,000-satellite catalog never stalls the frame.

using System;
using UdonSharp;
using UnityEngine;
using VRC.SDK3.StringLoading;
using VRC.SDKBase;
using VRC.Udon.Common.Interfaces;

[UdonBehaviourSyncMode(BehaviourSyncMode.None)]
public class SatelliteGlobe : UdonSharpBehaviour
{
    [Header("Data")]
    [Tooltip("Raw URL of data/orbits.csv")]
    [SerializeField] private VRCUrl orbitsUrl;
    [Tooltip("Minutes between re-downloads of the orbit data")]
    [SerializeField] private float refreshMinutes = 15f;

    [Header("Globe")]
    [Tooltip("Transform of the globe sphere; satellites are placed in its local space")]
    [SerializeField] private Transform globe;
    [Tooltip("Globe radius in world units (= Earth equatorial radius, 6378 km)")]
    [SerializeField] private float globeRadiusUnits = 0.5f;
    [Tooltip("Multiplier on altitude above the surface, for visibility (1 = true scale)")]
    [SerializeField] private float altitudeScale = 1f;

    [Header("Rendering")]
    [SerializeField] private ParticleSystem satelliteParticles;
    [SerializeField] private float particleSize = 0.004f;
    [SerializeField] private Color particleColor = Color.white;

    [Header("Performance")]
    [Tooltip("Satellites propagated per frame; the rest keep last position until their turn")]
    [SerializeField] private int updatesPerFrame = 300;
    [Tooltip("CSV lines parsed per frame while loading")]
    [SerializeField] private int parsesPerFrame = 500;

    private const double MU = 398600.4418;      // km^3/s^2
    private const double J2 = 1.08262668e-3;
    private const double RE = 6378.137;         // km
    private const double TWO_PI = 6.283185307179586;
    private const double DEG = 0.017453292519943295;

    // Parsed elements, one slot per satellite (Udon has no structs/lists)
    private double[] _epoch;      // unix seconds
    private double[] _cosInc;
    private double[] _sinInc;
    private double[] _raan0;      // rad
    private double[] _ecc;
    private double[] _argp0;      // rad
    private double[] _m0;         // rad
    private double[] _n;          // rad/s
    private double[] _sma;        // km
    private double[] _drift;      // 1.5 * J2 * (RE/p)^2 * n, rad/s
    private int _count;

    private ParticleSystem.Particle[] _particles;
    private string[] _pendingLines;
    private int _parseCursor;
    private int _updateCursor;
    private bool _ready;
    private bool _dirty;

    private void Start()
    {
        _RequestData();
    }

    public void _RequestData()
    {
        VRCStringDownloader.LoadUrl(orbitsUrl, (IUdonEventReceiver)this);
        SendCustomEventDelayedSeconds(nameof(_RequestData), refreshMinutes * 60f);
    }

    public override void OnStringLoadSuccess(IVRCStringDownload result)
    {
        _pendingLines = result.Result.Split('\n');
        _parseCursor = 1; // skip header row
        int capacity = _pendingLines.Length;
        _epoch = new double[capacity];
        _cosInc = new double[capacity];
        _sinInc = new double[capacity];
        _raan0 = new double[capacity];
        _ecc = new double[capacity];
        _argp0 = new double[capacity];
        _m0 = new double[capacity];
        _n = new double[capacity];
        _sma = new double[capacity];
        _drift = new double[capacity];
        _count = 0;
        _ParseChunk();
    }

    public override void OnStringLoadError(IVRCStringDownload result)
    {
        Debug.LogError($"[SatelliteGlobe] download failed: {result.Error}");
    }

    public void _ParseChunk()
    {
        int end = _parseCursor + parsesPerFrame;
        if (end > _pendingLines.Length) end = _pendingLines.Length;

        for (; _parseCursor < end; _parseCursor++)
        {
            // name,norad,epoch_unix,inc_deg,raan_deg,ecc,argp_deg,mean_anomaly_deg,mean_motion_rev_per_day
            string[] f = _pendingLines[_parseCursor].Split(',');
            if (f.Length < 9) continue;

            double epoch, inc, raan, ecc, argp, m0, revPerDay;
            if (!double.TryParse(f[2], out epoch)) continue;
            if (!double.TryParse(f[3], out inc)) continue;
            if (!double.TryParse(f[4], out raan)) continue;
            if (!double.TryParse(f[5], out ecc)) continue;
            if (!double.TryParse(f[6], out argp)) continue;
            if (!double.TryParse(f[7], out m0)) continue;
            if (!double.TryParse(f[8], out revPerDay)) continue;

            double n = revPerDay * TWO_PI / 86400.0;
            if (n <= 0.0 || ecc >= 1.0) continue;
            double a = Math.Pow(MU / (n * n), 1.0 / 3.0);
            double p = a * (1.0 - ecc * ecc);

            int i = _count;
            _epoch[i] = epoch;
            _cosInc[i] = Math.Cos(inc * DEG);
            _sinInc[i] = Math.Sin(inc * DEG);
            _raan0[i] = raan * DEG;
            _ecc[i] = ecc;
            _argp0[i] = argp * DEG;
            _m0[i] = m0 * DEG;
            _n[i] = n;
            _sma[i] = a;
            _drift[i] = 1.5 * J2 * (RE / p) * (RE / p) * n;
            _count++;
        }

        if (_parseCursor < _pendingLines.Length)
        {
            SendCustomEventDelayedFrames(nameof(_ParseChunk), 1);
            return;
        }

        _pendingLines = null;
        _particles = new ParticleSystem.Particle[_count];
        for (int i = 0; i < _count; i++)
        {
            _particles[i].startSize = particleSize;
            _particles[i].startColor = particleColor;
            _particles[i].remainingLifetime = float.MaxValue;
            _particles[i].startLifetime = float.MaxValue;
        }
        _updateCursor = 0;
        _ready = true;
        Debug.Log($"[SatelliteGlobe] loaded {_count} satellites");
    }

    private void Update()
    {
        if (!_ready) return;

        double now = GetUnixTime();
        double theta = Gmst(now);
        double cosT = Math.Cos(theta);
        double sinT = Math.Sin(theta);
        float scale = globeRadiusUnits / (float)RE;

        int end = _updateCursor + updatesPerFrame;
        for (int k = _updateCursor; k < end; k++)
        {
            int i = k % _count;

            double dt = now - _epoch[i];
            double e = _ecc[i];

            // Secular J2 drift of the node and perigee
            double raan = _raan0[i] - _drift[i] * _cosInc[i] * dt;
            double argp = _argp0[i]
                + 0.5 * _drift[i] * (5.0 * _cosInc[i] * _cosInc[i] - 1.0) * dt;

            // Kepler's equation (Newton)
            double m = _m0[i] + _n[i] * dt;
            double ecc_anom = m;
            for (int it = 0; it < 4; it++)
                ecc_anom -= (ecc_anom - e * Math.Sin(ecc_anom) - m)
                          / (1.0 - e * Math.Cos(ecc_anom));

            double nu = Math.Atan2(
                Math.Sqrt(1.0 - e * e) * Math.Sin(ecc_anom),
                Math.Cos(ecc_anom) - e);
            double r = _sma[i] * (1.0 - e * Math.Cos(ecc_anom));

            // Perifocal → inertial
            double u = argp + nu;
            double cosU = Math.Cos(u);
            double sinU = Math.Sin(u);
            double cosO = Math.Cos(raan);
            double sinO = Math.Sin(raan);
            double xi = r * (cosO * cosU - sinO * sinU * _cosInc[i]);
            double yi = r * (sinO * cosU + cosO * sinU * _cosInc[i]);
            double zi = r * (sinU * _sinInc[i]);

            // Inertial → Earth-fixed (globe) frame
            double x = xi * cosT + yi * sinT;
            double y = -xi * sinT + yi * cosT;

            // Altitude exaggeration: stretch along the radius vector
            if (altitudeScale != 1f)
            {
                double len = Math.Sqrt(x * x + y * y + zi * zi);
                double display = RE + (len - RE) * altitudeScale;
                double s = display / len;
                x *= s; y *= s; zi *= s;
            }

            // Unity is left-handed, Y-up: map ECEF (X,Y,Z) → (X, Z, Y)
            _particles[i].position = new Vector3(
                (float)x * scale, (float)zi * scale, (float)y * scale);
        }
        _updateCursor = end % _count;

        satelliteParticles.SetParticles(_particles, _count);
        if (globe != null)
            satelliteParticles.transform.SetPositionAndRotation(
                globe.position, globe.rotation);
    }

    private double GetUnixTime()
    {
        return (DateTime.UtcNow - new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc)).TotalSeconds;
    }

    private double Gmst(double unixSeconds)
    {
        // IAU 1982 GMST, same as satglobe/geodesy.py
        double jd = unixSeconds / 86400.0 + 2440587.5;
        double t = (jd - 2451545.0) / 36525.0;
        double seconds = 67310.54841
            + (876600.0 * 3600.0 + 8640184.812866) * t
            + 0.093104 * t * t
            - 6.2e-6 * t * t * t;
        seconds = seconds % 86400.0;
        if (seconds < 0.0) seconds += 86400.0;
        return seconds / 240.0 * DEG;
    }
}
