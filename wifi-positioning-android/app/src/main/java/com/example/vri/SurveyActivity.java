package com.example.vri;

import android.annotation.SuppressLint;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.PackageManager;
import android.media.Ringtone;
import android.media.RingtoneManager;
import android.net.Uri;
import android.net.wifi.ScanResult;
import android.net.wifi.WifiManager;
import android.net.wifi.rtt.WifiRttManager;
import android.net.wifi.rtt.RangingRequest;
import android.net.wifi.rtt.RangingResult;
import android.net.wifi.rtt.RangingResultCallback;
import android.os.Bundle;
import android.util.Log;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ProgressBar;
import android.widget.TableLayout;
import android.widget.TableRow;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowInsetsCompat;

import com.example.vri.models.ApiResponseModel;
import com.example.vri.models.WifiDataDTOModel;
import com.example.vri.models.WifiDataModel;
import com.example.vri.utils.APIHelper;
import com.example.vri.utils.Constanta;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import okhttp3.OkHttpClient;
import okhttp3.logging.HttpLoggingInterceptor;
import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;
import retrofit2.Retrofit;
import retrofit2.converter.gson.GsonConverterFactory;

public class SurveyActivity extends AppCompatActivity {
    private APIHelper apiHelper;
    private static final int LOCATION_PERMISSION_REQUEST_CODE = 1;
    private ProgressBar loadingProgressBar;
    private Button scan1Button;
    private Button scan10Button;
    private Button scan20Button;
    private EditText textX;
    private EditText textY;
    private WifiManager wifiManager;
    private WifiRttManager wifiRttManager;
    private boolean isFilterSSID = false;
    private List<ScanResult> results;
    List<WifiDataModel> wifiDataList = new ArrayList<>();
    private int numberOfScans = 20;
    private int wifiScannedLoop = 1;
    private boolean isSavedWifi = true;
    // All data collected as training (data_type=0). Use Settings → Split Data for 6:2:2 split.
    private static final int DATA_TYPE_TRAINING = 0;

    private boolean isReceiverRegistered = false;

    private void startRttScan(List<ScanResult> wifiScanResults) {
        if (wifiRttManager != null) {
            wifiDataList = new ArrayList<>();
            List<RangingRequest> rangingRequests = new ArrayList<>();

            for (ScanResult scanResult : wifiScanResults) {
                RangingRequest rangingRequest = new RangingRequest.Builder()
                        .addAccessPoint(scanResult)
                        .build();
                rangingRequests.add(rangingRequest);
            }
            if (ActivityCompat.checkSelfPermission(this, android.Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED || ActivityCompat.checkSelfPermission(this, android.Manifest.permission.NEARBY_WIFI_DEVICES) != PackageManager.PERMISSION_GRANTED) {
                return;
            }
//            wifiRttManager.startRanging(rangingRequests, getMainExecutor(), createRttListener());
        } // RTT / CSI

    }

    private final BroadcastReceiver wifiScanReceiver = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            if (WifiManager.SCAN_RESULTS_AVAILABLE_ACTION.equals(intent.getAction())) {
                // Check if location permission is granted
                if (ActivityCompat.checkSelfPermission(context, android.Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
                    return;
                }
                results = wifiManager.getScanResults();
                // Handle the scan results here
                updateWifiResults(results);
                for (ScanResult scanResult : results) {
                    String ssid = scanResult.SSID.isEmpty() ? " " : scanResult.SSID;
                    if (!isFilterSSID) {
                        wifiDataList.add(new WifiDataModel(ssid, scanResult.BSSID, scanResult.level, DATA_TYPE_TRAINING));
                    }
                    Log.d("WifiScan", "SSID: " + scanResult.SSID + ", BSSID: " + scanResult.BSSID + ", RSSI: " + scanResult.level);
                }

                if (wifiScannedLoop<numberOfScans) {
                    wifiScannedLoop++;
                    wifiManager.startScan();
                    // Pause // Thread.sleep(5)
                    // Calculate the variance, 0 && >90
                    // both rssi and average, option to choose which want to save
                }
                else {
                    Toast.makeText(getApplicationContext(),"Scan Finished",Toast.LENGTH_SHORT).show();
                    if (isSavedWifi) saveWifi();
                }
            }
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_survey);
        initViews();
        initPermissions();
        initObjects();
        initListeners();
    }

    private void initObjects() {
        wifiDataList = new ArrayList<>();
        wifiManager = (WifiManager) getApplicationContext().getSystemService(Context.WIFI_SERVICE);
        wifiRttManager = (WifiRttManager) getSystemService(Context.WIFI_RTT_RANGING_SERVICE);  // Correct service
        if (wifiRttManager == null) {
            // Handle the case where RTT is not supported
            Log.e("RTT", "RTT is not supported on this device.");
        }
        // Register the BroadcastReceiver to receive scan results
        registerReceiver(wifiScanReceiver, new IntentFilter(WifiManager.SCAN_RESULTS_AVAILABLE_ACTION));
        isReceiverRegistered = true;

        HttpLoggingInterceptor logging = new HttpLoggingInterceptor();
        // set your desired log level
        logging.setLevel(HttpLoggingInterceptor.Level.BODY);
        OkHttpClient.Builder httpClient = new OkHttpClient.Builder();
        // add your other interceptors …
        // add logging as last interceptor
        httpClient.addInterceptor(logging);

        Retrofit retrofit = new Retrofit.Builder()
                .baseUrl(new Constanta().apiUrl)
                .addConverterFactory(GsonConverterFactory.create())
                .client(httpClient.build())
                .build();

        apiHelper = retrofit.create(APIHelper.class);
    }

    private void initViews() {
        loadingProgressBar = findViewById(R.id.loadingProgressBar);
        scan10Button = findViewById(R.id.scan10Button);
        scan1Button = findViewById(R.id.scan1Button);
        scan20Button = findViewById(R.id.scan20Button);
        textX = findViewById(R.id.text_x);
        textY = findViewById(R.id.text_y);
    }

    private void initPermissions() {
        if (!isLocationPermissionGranted()) {
            // Location permission is not granted, request it
            requestLocationPermission();
        }
    }

    private void initListeners() {
        scan1Button.setOnClickListener(view -> scanWifi1());
        scan10Button.setOnClickListener(view -> scanWifi10());
        scan20Button.setOnClickListener(view -> scanWifi20());
    }

    private void getWifiData() {
        Map<String, String> parameters = new HashMap<>();
        parameters.put("userId", "1");
        parameters.put("_sort", "id");
        parameters.put("_order", "desc");

        Call<ApiResponseModel<Object>> call = apiHelper.getAllWifiDatas();
        call.enqueue(new Callback<ApiResponseModel<Object>>() {
            @Override
            public void onResponse(Call<ApiResponseModel<Object>> call, Response<ApiResponseModel<Object>> response) {
                if (!response.isSuccessful()) {
//                    textViewResult.setText("Code: " + response.code());
                    return;
                }

                ApiResponseModel apiResponseModel = response.body();
                Toast.makeText(getSupportActionBar().getThemedContext(), "Success", Toast.LENGTH_SHORT).show();

            }

            @Override
            public void onFailure(Call<ApiResponseModel<Object>> call, Throwable t) {

                Log.d("WifiScanError", t.getMessage());
            }
        });
    }

    public void saveWifi() {
        double x= Double.parseDouble(textX.getText().toString());
        double y= Double.parseDouble(textY.getText().toString());

        WifiDataDTOModel wifiDataDTO = new WifiDataDTOModel(x, y, wifiDataList);

        Call<ApiResponseModel<Object>> call = apiHelper.saveWifiData(wifiDataDTO);
        call.enqueue(new Callback<ApiResponseModel<Object>>() {
            @Override
            public void onResponse(Call<ApiResponseModel<Object>> call, Response<ApiResponseModel<Object>> response) {
                if (!response.isSuccessful()) {
                    Toast.makeText(getApplicationContext(), "Code: " + response.code(), Toast.LENGTH_SHORT).show();
                    return;
                }
                ApiResponseModel postResponse = response.body();
                Toast.makeText(getApplicationContext(), "Wifi Data Saved", Toast.LENGTH_LONG).show();

                Uri notification = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_NOTIFICATION);
                Ringtone r = RingtoneManager.getRingtone(getApplicationContext(), notification);
                r.play();
            }

            @Override
            public void onFailure(Call<ApiResponseModel<Object>> call, Throwable t) {
                Toast.makeText(getApplicationContext(), t.getMessage(), Toast.LENGTH_SHORT).show();
            }
        });
    }

    public void scanWifi1() {
        wifiScannedLoop=20;
        isSavedWifi=false;
        wifiDataList = new ArrayList<>();
        results = new ArrayList<>();
        if (isLocationPermissionGranted()) {
            loadingProgressBar.setVisibility(View.VISIBLE);
            wifiManager.startScan();
//            Toast.makeText(getApplicationContext(), "Scan Wifi Success", Toast.LENGTH_SHORT).show();
        } else {
            // Location permission is not granted, request it
            requestLocationPermission();
        }
    }

    public void scanWifi10() {
        wifiScannedLoop=11;
        isSavedWifi=true;
        wifiDataList = new ArrayList<>();
        results = new ArrayList<>();
        if (isLocationPermissionGranted()) {
            loadingProgressBar.setVisibility(View.VISIBLE);
            // Perform the Wi-Fi scan
            wifiManager.startScan();
//            Toast.makeText(getApplicationContext(), "Scan Wifi Success", Toast.LENGTH_SHORT).show();
        } else {
            // Location permission is not granted, request it
            requestLocationPermission();
        }
    }
    public void scanWifi20() {
        wifiScannedLoop=1;
        isSavedWifi=true;
        wifiDataList = new ArrayList<>();
        results = new ArrayList<>();
        if (isLocationPermissionGranted()) {
            loadingProgressBar.setVisibility(View.VISIBLE);
            // Perform the Wi-Fi scan
            wifiManager.startScan();
//            Toast.makeText(getApplicationContext(), "Scan Wifi Success", Toast.LENGTH_SHORT).show();
        } else {
            // Location permission is not granted, request it
            requestLocationPermission();
        }
    }

    // Update the UI with WiFi scan results
    @SuppressLint("SetTextI18n")
    private void updateWifiResults(List<ScanResult> results) {
        TableLayout tableLayout = findViewById(R.id.tableLayout);

        // Remove existing rows to refresh the display
        for (int i = tableLayout.getChildCount() - 1; i >= 0; i--) {
            tableLayout.removeViewAt(i);
        }
        boolean isHeaderAdded = false;

        // Iterate through the scan results and add rows to the table
        int count = 1;

        for (ScanResult scanResult : results) {
                TableRow row = new TableRow(this);
                row.setBackgroundColor(getResources().getColor(android.R.color.holo_blue_light));
                row.setPadding(5, 5, 5, 5);

                int margin = 4;
                // Add header only if it hasn't been added yet
                if (!isHeaderAdded) {
                    TableRow headerRow = new TableRow(this);
                    headerRow.setBackgroundColor(getResources().getColor(android.R.color.holo_green_light));
                    headerRow.setPadding(5, 5, 5, 5);

                    // Add margins to header cells

                    TextView noHeader = new TextView(this);
                    noHeader.setText("No");
                    noHeader.setLayoutParams(new TableRow.LayoutParams(0, TableRow.LayoutParams.WRAP_CONTENT, 1f));
                    noHeader.setPadding(margin, 0, margin, 0);

                    TextView ssidHeader = new TextView(this);
                    ssidHeader.setText("SSID");
                    ssidHeader.setLayoutParams(new TableRow.LayoutParams(0, TableRow.LayoutParams.WRAP_CONTENT, 1f));
                    ssidHeader.setPadding(margin, 0, margin, 0);

                    TextView bssidHeader = new TextView(this);
                    bssidHeader.setText("BSSID");
                    bssidHeader.setLayoutParams(new TableRow.LayoutParams(0, TableRow.LayoutParams.WRAP_CONTENT, 1f));
                    bssidHeader.setPadding(margin, 0, margin, 0);

                    TextView rssiHeader = new TextView(this);
                    rssiHeader.setText("RSSI");
                    rssiHeader.setLayoutParams(new TableRow.LayoutParams(0, TableRow.LayoutParams.WRAP_CONTENT, 1f));
                    rssiHeader.setPadding(margin, 0, margin, 0);

                    headerRow.addView(noHeader);
                    headerRow.addView(ssidHeader);
                    headerRow.addView(bssidHeader);
                    headerRow.addView(rssiHeader);

                    tableLayout.addView(headerRow);
                    isHeaderAdded = true; // Mark header as added
                }

                TextView noTextView = new TextView(this);
                noTextView.setText(String.valueOf(count));
                noTextView.setLayoutParams(new TableRow.LayoutParams(0, TableRow.LayoutParams.WRAP_CONTENT, 1f));
                noTextView.setPadding(margin, 0, margin, 0);

                TextView ssidTextView = new TextView(this);
                ssidTextView.setText(scanResult.SSID);
                ssidTextView.setLayoutParams(new TableRow.LayoutParams(0, TableRow.LayoutParams.WRAP_CONTENT, 1f));
                ssidTextView.setPadding(margin, 0, margin, 0);

                TextView bssidTextView = new TextView(this);
                bssidTextView.setText(scanResult.BSSID);
                bssidTextView.setLayoutParams(new TableRow.LayoutParams(0, TableRow.LayoutParams.WRAP_CONTENT, 1f));
                bssidTextView.setPadding(margin, 0, margin, 0);

                TextView rssiTextView = new TextView(this);
                rssiTextView.setText(String.valueOf(scanResult.level));
                rssiTextView.setLayoutParams(new TableRow.LayoutParams(0, TableRow.LayoutParams.WRAP_CONTENT, 1f));
                rssiTextView.setPadding(margin, 0, margin, 0);

                row.addView(noTextView);
                row.addView(ssidTextView);
                row.addView(bssidTextView);
                row.addView(rssiTextView);

                tableLayout.addView(row);

                count++;
        }

        loadingProgressBar.setVisibility(View.GONE);
    }

    private boolean isLocationPermissionGranted() {
        return ContextCompat.checkSelfPermission(this, android.Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED;
    }

    // Helper method to request location permission
    private void requestLocationPermission() {
        ActivityCompat.requestPermissions(this,
                new String[]{android.Manifest.permission.ACCESS_FINE_LOCATION},
                LOCATION_PERMISSION_REQUEST_CODE);
    }

    // Handle the result of the permission request
    @Override
    public void onRequestPermissionsResult(int requestCode, @NonNull String[] permissions, @NonNull int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == LOCATION_PERMISSION_REQUEST_CODE) {
            if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                // Permission granted, perform the Wi-Fi scan
                Log.d("WifiScan", "Location permission granted");
            } else {
                // Permission denied, handle accordingly (e.g., show a message)
                Log.d("WifiScan", "Location permission denied");
            }
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        // Unregister the BroadcastReceiver when the activity is destroyed
        if (isReceiverRegistered) {
            unregisterReceiver(wifiScanReceiver);
            isReceiverRegistered = false;
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        // 停止Wi-Fi扫描并取消注册BroadcastReceiver
        if (isReceiverRegistered) {
            unregisterReceiver(wifiScanReceiver);
            isReceiverRegistered = false;
        }
        // 如果当前正在执行扫描，可以考虑额外的逻辑来停止扫描
        // 这取决于你的具体实现和需求
    }

    @Override
    protected void onResume() {
        super.onResume();
        // 重新注册BroadcastReceiver以继续接收Wi-Fi扫描结果
        if (!isReceiverRegistered) {
            registerReceiver(wifiScanReceiver, new IntentFilter(WifiManager.SCAN_RESULTS_AVAILABLE_ACTION));
            isReceiverRegistered = true;
        }
    }
}