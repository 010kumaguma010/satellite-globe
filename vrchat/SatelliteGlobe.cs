using UdonSharp;
using UnityEngine;
using VRC.SDK3.StringLoading;
using VRC.SDKBase;
using VRC.Udon.Common.Interfaces;

/// <summary>
/// Fetches satellite positions from the CSV, places satellite markers on a globe,
/// and auto-refreshes every <see cref="refreshIntervalSeconds"/> seconds.
///
/// Setup:
///   1. Attach this script to a GameObject at the center of your globe mesh.
///   2. Assign a small sphere (or any prefab) to SatellitePrefab.
///   3. Set GlobeRadius to match the radius of your globe mesh in Unity units.
///   4. Set AltitudeScale so orbital altitudes look right (default: LEO ~= thin shell).
///   5. Set MaxSatellites (500 is safe; 15 000 may tank FPS).
/// </summary>
[UdonBehaviourSyncMode(BehaviourSyncMode.None)]
public class SatelliteGlobe : UdonSharpBehaviour
{
    [Header("Data Source")]
    [SerializeField] private VRCUrl csvUrl = new VRCUrl(
        "https://raw.githubusercontent.com/010kumaguma010/satellite-globe/main/data/satellites.csv"
    );
    [Tooltip("How often to re-fetch the CSV (seconds). Default = 600 = 10 min.")]
    [SerializeField] private float refreshIntervalSeconds = 600f;

    [Header("Globe")]
    [Tooltip("Radius of your globe mesh in Unity units.")]
    [SerializeField] private float globeRadius = 1f;
    [Tooltip("Scale factor: altitude_km * this = extra radius in Unity units. " +
             "e.g. 0.0001 makes a 400 km orbit extend 0.04 units above the surface.")]
    [SerializeField] private float altitudeScale = 0.0001f;

    [Header("Satellites")]
    [Tooltip("Prefab to use as a satellite marker.")]
    [SerializeField] private GameObject satellitePrefab;
    [Tooltip("Max satellites to display. Keep ≤ 1000 for stable frame rates.")]
    [SerializeField] private int maxSatellites = 500;

    // Object pool — pre-allocated in Start, repositioned on each refresh
    private GameObject[] _pool;
    private int _activeCount;

    void Start()
    {
        _pool = new GameObject[maxSatellites];
        for (int i = 0; i < maxSatellites; i++)
        {
            _pool[i] = Instantiate(satellitePrefab, transform);
            _pool[i].SetActive(false);
        }

        FetchCSV();
    }

    /// <summary>Called on timer to download the latest CSV.</summary>
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
        Debug.LogWarning($"[SatelliteGlobe] CSV fetch failed (code {result.ErrorCode}). Retrying in {refreshIntervalSeconds}s.");
        SendCustomEventDelayedSeconds(nameof(FetchCSV), refreshIntervalSeconds);
    }

    private void PlaceSatellites(string csv)
    {
        // Disable all pooled objects first
        for (int i = 0; i < _activeCount; i++)
            _pool[i].SetActive(false);

        string[] lines = csv.Split('\n');
        int count = 0;

        // Skip header row (i = 1)
        for (int i = 1; i < lines.Length && count < maxSatellites; i++)
        {
            string line = lines[i].Trim();
            if (string.IsNullOrEmpty(line)) continue;

            string[] cols = line.Split(',');
            if (cols.Length < 4) continue;

            if (!float.TryParse(cols[1], System.Globalization.NumberStyles.Float,
                    System.Globalization.CultureInfo.InvariantCulture, out float lat)) continue;
            if (!float.TryParse(cols[2], System.Globalization.NumberStyles.Float,
                    System.Globalization.CultureInfo.InvariantCulture, out float lon)) continue;
            if (!float.TryParse(cols[3], System.Globalization.NumberStyles.Float,
                    System.Globalization.CultureInfo.InvariantCulture, out float altKm)) continue;

            Vector3 pos = LatLonAltToLocal(lat, lon, altKm);
            _pool[count].transform.localPosition = pos;
            _pool[count].SetActive(true);
            count++;
        }

        _activeCount = count;
        Debug.Log($"[SatelliteGlobe] {count} satellites placed.");
    }

    /// <summary>
    /// Converts geographic coordinates to a local-space position on the globe.
    ///
    /// Coordinate convention (Y-up):
    ///   North Pole  →  +Y
    ///   (lat=0, lon=0) →  +X (facing viewer when globe faces forward)
    ///   (lat=0, lon=90) → +Z
    /// </summary>
    private Vector3 LatLonAltToLocal(float latDeg, float lonDeg, float altKm)
    {
        float r = globeRadius + altKm * altitudeScale;
        float latRad = latDeg * Mathf.Deg2Rad;
        float lonRad = lonDeg * Mathf.Deg2Rad;

        float cosLat = Mathf.Cos(latRad);
        return new Vector3(
            r * cosLat * Mathf.Cos(lonRad),  // X: prime meridian / east
            r * Mathf.Sin(latRad),            // Y: north
            r * cosLat * Mathf.Sin(lonRad)   // Z: east of prime meridian
        );
    }
}
