using UdonSharp;
using UnityEngine;
using VRC.SDK3.StringLoading;
using VRC.SDKBase;
using VRC.Udon.Common.Interfaces;

/// <summary>
/// Fetches satellite positions from the CSV and places color-coded markers on a globe.
/// Satellites are split into three altitude bands, each with its own prefab and display limit.
///
///   LEO  (       0 –  2,000 km) visual shell 1.10 – 1.35 × globeRadius  (e.g. white/cyan)
///   MEO  (   2,000 – 35,785 km) visual shell 1.60 – 1.90 × globeRadius  (e.g. yellow)
///   GEO+ (≥ 35,785 km         ) visual shell 2.10 – 2.50 × globeRadius  (e.g. orange)
///
/// Setup:
///   1. Attach to a GameObject at the center of your globe mesh.
///   2. Create three small Sphere prefabs (scale ~0.015) with different-colored materials.
///   3. Assign them to Leo Prefab / Meo Prefab / Geo Prefab in the Inspector.
///   4. Set Globe Radius to match your globe mesh radius in Unity units.
///   5. Add the CSV URL to VRChat SDK > Allow Listed URLs.
/// </summary>
[UdonBehaviourSyncMode(BehaviourSyncMode.None)]
public class SatelliteGlobe : UdonSharpBehaviour
{
    [Header("Data Source")]
    [SerializeField] private VRCUrl csvUrl = new VRCUrl(
        "https://raw.githubusercontent.com/010kumaguma010/satellite-globe/main/data/satellites.csv"
    );
    [Tooltip("Re-fetch interval in seconds (default 600 = 10 min).")]
    [SerializeField] private float refreshIntervalSeconds = 600f;

    [Header("Globe")]
    [Tooltip("Radius of your globe mesh in Unity units.")]
    [SerializeField] private float globeRadius = 1f;

    [Header("Satellite Prefabs")]
    [Tooltip("LEO (< 2,000 km) marker — e.g. white or cyan sphere")]
    [SerializeField] private GameObject leoPrefab;
    [Tooltip("MEO (2,000 – 35,785 km) marker — e.g. yellow sphere (GPS etc.)")]
    [SerializeField] private GameObject meoPrefab;
    [Tooltip("GEO+ (≥ 35,785 km) marker — e.g. orange sphere (geostationary etc.)")]
    [SerializeField] private GameObject geoPrefab;

    [Header("Display Limits per Band")]
    [SerializeField] private int maxLeo = 500;
    [SerializeField] private int maxMeo = 100;
    [SerializeField] private int maxGeo = 150;

    // Object pools — allocated once in Start, repositioned each refresh
    private GameObject[] _leoPool;
    private GameObject[] _meoPool;
    private GameObject[] _geoPool;
    private int _leoActive;
    private int _meoActive;
    private int _geoActive;

    void Start()
    {
        _leoPool = BuildPool(leoPrefab, maxLeo);
        _meoPool = BuildPool(meoPrefab, maxMeo);
        _geoPool = BuildPool(geoPrefab, maxGeo);
        FetchCSV();
    }

    private GameObject[] BuildPool(GameObject prefab, int size)
    {
        var pool = new GameObject[size];
        for (int i = 0; i < size; i++)
        {
            pool[i] = Instantiate(prefab, transform);
            pool[i].SetActive(false);
        }
        return pool;
    }

    public void FetchCSV()
    {
        VRCStringDownloader.LoadUrl(csvUrl, (IUdonEventReceiver)this);
    }

    public override void OnStringLoadSuccess(IVRCStringDownload result)
    {
        PlaceSatellites(result.Result);
        SendCustomEventDelayedSeconds(nameof(FetchCSV), refreshIntervalSeconds);
    }

    public override void OnStringLoadError(IVRCStringDownload result)
    {
        Debug.LogWarning($"[SatelliteGlobe] Fetch failed (code {result.ErrorCode}). Retrying in {refreshIntervalSeconds}s.");
        SendCustomEventDelayedSeconds(nameof(FetchCSV), refreshIntervalSeconds);
    }

    private void PlaceSatellites(string csv)
    {
        HidePool(_leoPool, _leoActive);
        HidePool(_meoPool, _meoActive);
        HidePool(_geoPool, _geoActive);
        _leoActive = 0;
        _meoActive = 0;
        _geoActive = 0;

        string[] lines = csv.Split('\n');

        for (int i = 1; i < lines.Length; i++)
        {
            if (_leoActive >= maxLeo && _meoActive >= maxMeo && _geoActive >= maxGeo)
                break;

            string line = lines[i].Trim();
            if (line.Length == 0) continue;

            string[] cols = line.Split(',');
            if (cols.Length < 4) continue;

            float lat, lon, altKm;
            if (!float.TryParse(cols[1], out lat)) continue;
            if (!float.TryParse(cols[2], out lon)) continue;
            if (!float.TryParse(cols[3], out altKm)) continue;
            if (altKm < 0f) continue;

            float r = AltToVisualRadius(altKm);
            Vector3 pos = LatLonToLocal(lat, lon, r);

            if (altKm < 2000f)
            {
                if (_leoActive >= maxLeo) continue;
                _leoPool[_leoActive].transform.localPosition = pos;
                _leoPool[_leoActive].SetActive(true);
                _leoActive++;
            }
            else if (altKm < 35785f)
            {
                if (_meoActive >= maxMeo) continue;
                _meoPool[_meoActive].transform.localPosition = pos;
                _meoPool[_meoActive].SetActive(true);
                _meoActive++;
            }
            else
            {
                if (_geoActive >= maxGeo) continue;
                _geoPool[_geoActive].transform.localPosition = pos;
                _geoPool[_geoActive].SetActive(true);
                _geoActive++;
            }
        }

        Debug.Log($"[SatelliteGlobe] Placed — LEO: {_leoActive}, MEO: {_meoActive}, GEO+: {_geoActive}");
    }

    private void HidePool(GameObject[] pool, int count)
    {
        for (int i = 0; i < count; i++)
            pool[i].SetActive(false);
    }

    /// <summary>
    /// Maps real altitude to a visually compressed shell radius so that all three
    /// orbit bands are clearly visible at any globe scale.
    ///
    ///   LEO   0 – 2,000 km  →  1.10 – 1.35 × globeRadius
    ///   MEO   2,000 – 35,785 km  →  1.60 – 1.90 × globeRadius
    ///   GEO+  ≥ 35,785 km        →  2.10 – 2.50 × globeRadius
    /// </summary>
    private float AltToVisualRadius(float altKm)
    {
        float g = globeRadius;
        if (altKm < 2000f)
            return g * (1.10f + (altKm / 2000f) * 0.25f);
        if (altKm < 35785f)
            return g * (1.60f + ((altKm - 2000f) / 33785f) * 0.30f);
        return g * (2.10f + Mathf.Min((altKm - 35785f) / 20000f, 1f) * 0.40f);
    }

    /// <summary>
    /// Converts lat/lon + pre-computed radius to a local-space position.
    /// Convention (Y-up): North Pole → +Y, (lat=0, lon=0) → +X, (lat=0, lon=90°E) → +Z.
    /// </summary>
    private Vector3 LatLonToLocal(float latDeg, float lonDeg, float r)
    {
        float latRad = latDeg * Mathf.Deg2Rad;
        float lonRad = lonDeg * Mathf.Deg2Rad;
        float cosLat = Mathf.Cos(latRad);
        return new Vector3(
            r * cosLat * Mathf.Cos(lonRad),
            r * Mathf.Sin(latRad),
            r * cosLat * Mathf.Sin(lonRad)
        );
    }
}
