using UdonSharp;
using UnityEngine;
using VRC.SDK3.StringLoading;
using VRC.SDKBase;
using VRC.Udon.Common.Interfaces;

[UdonBehaviourSyncMode(BehaviourSyncMode.None)]
public class SatelliteGlobe : UdonSharpBehaviour
{
    [Header("Data Source")]
    // Inspector の Csv Url 欄に以下を入力してください:
    // https://raw.githubusercontent.com/010kumaguma010/satellite-globe/main/data/satellites.csv
    [SerializeField] private VRCUrl csvUrl;
    [SerializeField] private float refreshIntervalSeconds = 600f;

    [Header("Globe")]
    [SerializeField] private float globeRadius = 1f;

    [Header("Satellite Prefabs")]
    [SerializeField] private GameObject leoPrefab;
    [SerializeField] private GameObject meoPrefab;
    [SerializeField] private GameObject geoPrefab;

    [Header("Display Limits")]
    [SerializeField] private int maxLeo = 500;
    [SerializeField] private int maxMeo = 100;
    [SerializeField] private int maxGeo = 150;

    private GameObject[] _leoPool;
    private GameObject[] _meoPool;
    private GameObject[] _geoPool;
    private int _leoActive;
    private int _meoActive;
    private int _geoActive;

    void Start()
    {
        _leoPool = new GameObject[maxLeo];
        for (int i = 0; i < maxLeo; i++)
        {
            _leoPool[i] = Instantiate(leoPrefab, transform);
            _leoPool[i].SetActive(false);
        }

        _meoPool = new GameObject[maxMeo];
        for (int i = 0; i < maxMeo; i++)
        {
            _meoPool[i] = Instantiate(meoPrefab, transform);
            _meoPool[i].SetActive(false);
        }

        _geoPool = new GameObject[maxGeo];
        for (int i = 0; i < maxGeo; i++)
        {
            _geoPool[i] = Instantiate(geoPrefab, transform);
            _geoPool[i].SetActive(false);
        }

        FetchCSV();
    }

    public void FetchCSV()
    {
        VRCStringDownloader.LoadUrl(csvUrl, (IUdonEventReceiver)this);
    }

    public override void OnStringLoadSuccess(IVRCStringDownload result)
    {
        PlaceSatellites(result.Result);
        SendCustomEventDelayedSeconds("FetchCSV", refreshIntervalSeconds);
    }

    public override void OnStringLoadError(IVRCStringDownload result)
    {
        Debug.LogWarning("[SatelliteGlobe] Fetch failed. Retrying.");
        SendCustomEventDelayedSeconds("FetchCSV", refreshIntervalSeconds);
    }

    private void PlaceSatellites(string csv)
    {
        for (int i = 0; i < _leoActive; i++) _leoPool[i].SetActive(false);
        for (int i = 0; i < _meoActive; i++) _meoPool[i].SetActive(false);
        for (int i = 0; i < _geoActive; i++) _geoPool[i].SetActive(false);
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

            float lat;
            float lon;
            float altKm;
            if (!float.TryParse(cols[1], out lat)) continue;
            if (!float.TryParse(cols[2], out lon)) continue;
            if (!float.TryParse(cols[3], out altKm)) continue;
            if (altKm < 0f) continue;

            float r;
            if (altKm < 2000f)
                r = globeRadius * (1.10f + (altKm / 2000f) * 0.25f);
            else if (altKm < 35785f)
                r = globeRadius * (1.60f + ((altKm - 2000f) / 33785f) * 0.30f);
            else
                r = globeRadius * (2.10f + Mathf.Min((altKm - 35785f) / 20000f, 1f) * 0.40f);

            float latRad = lat * Mathf.Deg2Rad;
            float lonRad = lon * Mathf.Deg2Rad;
            float cosLat = Mathf.Cos(latRad);
            Vector3 pos = new Vector3(
                r * cosLat * Mathf.Cos(lonRad),
                r * Mathf.Sin(latRad),
                r * cosLat * Mathf.Sin(lonRad)
            );

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

        Debug.Log("[SatelliteGlobe] Placed LEO:" + _leoActive + " MEO:" + _meoActive + " GEO:" + _geoActive);
    }
}
