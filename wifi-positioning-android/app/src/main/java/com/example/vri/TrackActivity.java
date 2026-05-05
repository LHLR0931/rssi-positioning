package com.example.vri;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.ActivityInfo;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.net.Uri;
import android.net.wifi.ScanResult;
import android.net.wifi.WifiManager;
import android.os.Bundle;
import android.util.Log;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowInsetsCompat;

import com.example.vri.models.ApiResponseModel;
import com.example.vri.custom.IndoorMapMultipleView;
import com.example.vri.models.PointModel;
import com.example.vri.models.PredictionModel;
import com.example.vri.models.WifiDataDTOModel;
import com.example.vri.models.WifiDataModel;
import com.example.vri.utils.APIHelper;
import com.example.vri.utils.Constanta;

import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import java.util.Map;

import okhttp3.OkHttpClient;
import okhttp3.logging.HttpLoggingInterceptor;
import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;
import retrofit2.Retrofit;
import retrofit2.converter.gson.GsonConverterFactory;

public class TrackActivity extends AppCompatActivity {
    private APIHelper apiHelper;
    private static final int LOCATION_PERMISSION_REQUEST_CODE = 1;
    private static final int PICK_IMAGE_REQUEST = 1001;
    private Button predictButtonKnn;
    private Button predictButtonRf;
    private Button backgroundButton;
    private Button predictFingerKnn;
    private Button predictFingerRf;
    private Button predictCNN;
    private Button predictGNN;
    private android.widget.TextView errorTextView;
    private IndoorMapMultipleView indoorMapView;
    private WifiManager wifiManager;
    private List<ScanResult> results;
    List<WifiDataModel> wifiDataList = new ArrayList<>();
    private boolean isPredict = false;

    private PredictionType currentPredictionType = PredictionType.KNN;
    private EditText textX;
    private EditText textY;
    private int numberOfScans = 5;
    private int wifiScannedLoop = 1;
    private boolean isFilterSSID = false;

    private boolean isReceiverRegistered = false;

    private enum PredictionType {
        KNN,
        RF,
        CNN,
        GNN,
        KNN_FINGER,
        RF_FINGER
    }

    List<String> allowedBSSIDs = Arrays.asList("88:9c:ad:12:ff:2c", "88:9c:ad:0f:b3:cc", "88:9c:ad:0f:b3:cc", "88:9c:ad:12:ff:2c", "88:9c:ad:12:fe:8c");
//    List<String> allowedBSSIDs = Arrays.asList("d4:d4:da:71:e6:d1", "d0:15:a6:b5:a1:b1", "d0:15:a6:b5:a1:b0", "d4:d4:da:71:e3:41");
//    List<String> allowedBSSIDs2 = Arrays.asList("d0:15:a6:b5:a1:b1", "d0:15:a6:b5:a1:b0", "d0:15:a6:b5:a1:a1", "d0:15:a6:b5:a1:a0");
//    List<String> allowedBSSIDs3 = Arrays.asList("b0:e4:d5:39:26:89", "cc:f4:11:8b:29:4d", "b0:e4:d5:01:26:f5", "b0:e4:d5:91:ba:5d", "b0:e4:d5:96:3b:95", "f8:1a:2b:06:3c:0b", "14:22:3b:2a:86:f5", "14:22:3b:16:5a:bd");
    private final BroadcastReceiver wifiScanReceiver = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            if (WifiManager.SCAN_RESULTS_AVAILABLE_ACTION.equals(intent.getAction())) {
                // Check if location permission is granted
                if (ActivityCompat.checkSelfPermission(context, android.Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
                    return;
                }
                results = wifiManager.getScanResults();

                // Sort the ScanResults based on RSSI
                Collections.sort(results, new Comparator<ScanResult>() {
                    @Override
                    public int compare(ScanResult result1, ScanResult result2) {
                        return Integer.compare(result2.level, result1.level); // Descending order
                    }
                });

                // Take the best 3 non-zero RSSI ScanResults
                List<ScanResult> bestThreeResults = new ArrayList<>();
                for (ScanResult result : results) {
                    if (result.level != 0) {
                        bestThreeResults.add(result);
                        if (bestThreeResults.size() >= 3) {
                            break;
                        }
                    }
                }

                // Handle the scan results here
                for (ScanResult scanResult : results) {
                    String ssid = scanResult.SSID.isEmpty() ? " " : scanResult.SSID;
                    if (!isFilterSSID || allowedBSSIDs.contains(scanResult.BSSID)) {
                        wifiDataList.add(new WifiDataModel(ssid, scanResult.BSSID, scanResult.level));
                    }
                    Log.d("WifiScan", "SSID: " + scanResult.SSID + ", BSSID: " + scanResult.BSSID + ", RSSI: " + scanResult.level);
                }

                if (wifiScannedLoop < numberOfScans) {
                    wifiScannedLoop++;
                    wifiManager.startScan();
                } else {
                    Toast.makeText(getApplicationContext(), "Scan Finished", Toast.LENGTH_SHORT).show();
//
                    double inputX = getInputX();
                    double inputY = getInputY();
                    WifiDataDTOModel wifiDataDTO = new WifiDataDTOModel(inputX, inputY, wifiDataList);

                    Call<ApiResponseModel<PredictionModel>> call = null;
                    switch (currentPredictionType) {
                        case RF:
                            call = apiHelper.predictPosition(wifiDataDTO);
                            break;
                        case KNN:
                            call = apiHelper.predictPosition(wifiDataDTO);
                            break;
                        case RF_FINGER:
                            call = apiHelper.fingerPredictPosition(wifiDataDTO);
                            break;
                        case KNN_FINGER:
                            call = apiHelper.fingerPredictPosition(wifiDataDTO);
                            break;
                        case CNN:
                            call = apiHelper.cnnPredictPosition(wifiDataDTO);
                            break;
                       case GNN:
                            call = apiHelper.gnnPredictPosition(wifiDataDTO);
                           break;


                    }

                    call.enqueue(new Callback<ApiResponseModel<PredictionModel>>() {
                        @Override
                        public void onResponse(Call<ApiResponseModel<PredictionModel>> call, Response<ApiResponseModel<PredictionModel>> response) {
                            if (!response.isSuccessful()) {
                                Toast.makeText(getApplicationContext(), "Code: " + response.code(), Toast.LENGTH_SHORT).show();
                                return;
                            }

                            ApiResponseModel apiResponseModel = response.body();
                            PredictionModel data = (PredictionModel) apiResponseModel.getData();

                            double predX = 0, predY = 0;
                            switch (currentPredictionType) {
                                case RF:
                                    predX = data.getClosest_rf_result().getX();
                                    predY = data.getClosest_rf_result().getY();
                                    break;
                                case KNN:
                                    predX = data.getClosest_knn_result().getX();
                                    predY = data.getClosest_knn_result().getY();
                                    break;
                                case CNN:
                                    predX = data.getCnn_predictions().getX();
                                    predY = data.getCnn_predictions().getY();
                                    break;
                                case RF_FINGER:
                                    predX = data.getFinger_rf_predictions().getX();
                                    predY = data.getFinger_rf_predictions().getY();
                                    break;
                                case KNN_FINGER:
                                    predX = data.getFinger_knn_predictions().getX();
                                    predY = data.getFinger_knn_predictions().getY();
                                    break;
                                case GNN:
                                    predX = data.getGnn_predictions().getX();
                                    predY = data.getGnn_predictions().getY();
                                    break;
                            }
                            indoorMapView.addSpecificPoint(predX, predY);

                            double errorMeters = data.getError_meters();
                            double actX = data.getActual_x();
                            double actY = data.getActual_y();
                            String label = currentPredictionType.name();
                            String errorMsg = String.format(
                                "[%s]  Actual(%.2f, %.2f)  →  Pred(%.2f, %.2f)  |  Error: %.2f m",
                                label, actX, actY, predX, predY, errorMeters);
                            errorTextView.setText(errorMsg);

                            Toast.makeText(getApplicationContext(), "Showing Prediction", Toast.LENGTH_LONG).show();
                        }

                        @Override
                        public void onFailure(Call<ApiResponseModel<PredictionModel>> call, Throwable t) {
                            Log.d("WifiScanError", t.getMessage());
                        }
                    });
                }

            }
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_track);
//        setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_PORTRAIT);

        initViews();
        initPermissions();
        initObjects();
        initListeners();

    }

    private void getSurveyXY() {
        Call<ApiResponseModel<Object>> call = apiHelper.getAllSurveyDatas();
        call.enqueue(new Callback<ApiResponseModel<Object>>() {
            @Override
            public void onResponse(Call<ApiResponseModel<Object>> call, Response<ApiResponseModel<Object>> response) {
                if (!response.isSuccessful()) {
//                    textViewResult.setText("Code: " + response.code());
                    return;
                }
                ApiResponseModel apiResponseModel = response.body();
//                List<PointModel> surveyData= (List<PointModel>) apiResponseModel.getData();
                List<Map<String, Object>> surveyData = (List<Map<String, Object>>) apiResponseModel.getData();
                List<PointModel> pointModels = new ArrayList<>();
                for (Map<String, Object> surveyPoint : surveyData) {
                    PointModel pointModel = new PointModel();

                    // Extract and set properties of pointModel based on surveyPoint
                    pointModel.setX((Double) surveyPoint.get("x"));
                    pointModel.setY((Double) surveyPoint.get("y"));
                    // Repeat for other properties
                    // Add the converted pointModel to the new list
                    pointModels.add(pointModel);
                }
                indoorMapView.setSurveyPoints(pointModels);
            }

            @Override
            public void onFailure(Call<ApiResponseModel<Object>> call, Throwable t) {
                Log.d("WifiScanError", t.getMessage());
            }
        });
    }

    private void initObjects() {
        wifiDataList = new ArrayList<>();
        wifiManager = (WifiManager) getApplicationContext().getSystemService(Context.WIFI_SERVICE);
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
//        indoorMapView.addSpecificPoint(0,11.5);
        List<PointModel> anchorPoints = new ArrayList<>(); // For Access Point
//        anchorPoints.add(new PointModel(3.0, 5.0)); // AP 1
//        anchorPoints.add(new PointModel(5.5, 7.5)); // AP 2
//        anchorPoints.add(new PointModel(0.5, 8.0)); // AP 1
//        anchorPoints.add(new PointModel(4.0, 6.0)); // AP 2
//        anchorPoints.add(new PointModel(2.0, 10.0)); // AP 1
//        anchorPoints.add(new PointModel(4.0, 10.0)); // AP 2
//        anchorPoints.add(new PointModel(2.0, 14.0)); // AP 1
//        anchorPoints.add(new PointModel(4.0, 14.0)); // AP 2
//        anchorPoints.add(new PointModel(9.0, 0.0)); // AP 3
//        anchorPoints.add(new PointModel(13.5, 0.0)); // AP 2
//        anchorPoints.add(new PointModel(18.0, 0.0)); // AP 3
//        anchorPoints.add(new PointModel(0.0, 9.0)); // AP 1
//        anchorPoints.add(new PointModel(4.5, 9.0)); // AP 2
//        anchorPoints.add(new PointModel(9.0, 9.0)); // AP 3
//        anchorPoints.add(new PointModel(13.5, 9.0)); // AP 2
//        anchorPoints.add(new PointModel(18.0, 9.0)); // AP 3
//        anchorPoints.add(new PointModel(0.0, 18.0)); // AP 1
//        anchorPoints.add(new PointModel(4.5, 18.0)); // AP 2
//        anchorPoints.add(new PointModel(9.0, 18.0)); // AP 3
//        anchorPoints.add(new PointModel(13.5, 18.0)); // AP 2
//        anchorPoints.add(new PointModel(18.0, 18.0)); // AP 3
//        anchorPoints.add(new PointModel(0.0, 27.0)); // AP 1
//        anchorPoints.add(new PointModel(4.5, 27.0)); // AP 2
//        anchorPoints.add(new PointModel(9.0, 27.0)); // AP 3
//        anchorPoints.add(new PointModel(13.5, 27.0)); // AP 2
//        anchorPoints.add(new PointModel(18.0, 27.0)); // AP 3
//        anchorPoints.add(new PointModel(0.0, 36.0)); // AP 1
//        anchorPoints.add(new PointModel(4.5, 36.0)); // AP 2
//        anchorPoints.add(new PointModel(9.0, 36.0)); // AP 3
        indoorMapView.setAnchorPoints(anchorPoints);
        getSurveyXY();
    }

    private void initViews() {
        indoorMapView = findViewById(R.id.indoorMapView);
        predictButtonKnn = findViewById(R.id.predictButtonKnn);
        predictButtonRf = findViewById(R.id.predictButtonRf);
        backgroundButton = findViewById(R.id.backgroundButton);
        predictFingerKnn = findViewById(R.id.predictFingerKnn);
        predictFingerRf = findViewById(R.id.predictFingerRf);
        predictCNN = findViewById(R.id.predictCNN);
        predictGNN = findViewById(R.id.predictGNN);
        errorTextView = findViewById(R.id.errorTextView);
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
        predictButtonKnn.setOnClickListener(view -> predictKnn());
        predictButtonRf.setOnClickListener(view -> predictRf());
        backgroundButton.setOnClickListener(view -> setBackground());
        predictFingerKnn.setOnClickListener(view -> predictFingerKnn());
        predictFingerRf.setOnClickListener(view -> predictFingerRf());
        predictCNN.setOnClickListener(view -> predictCNN());
        predictGNN.setOnClickListener(view -> predictGNN());
//        textY.setOnFocusChangeListener(new View.OnFocusChangeListener() {
//            @Override
//            public void onFocusChange(View v, boolean hasFocus) {
//                if (!textY.getText().equals("")) {
//                    indoorMapView.setCurrentPosition(Double.parseDouble(textX.getText().toString()), Double.parseDouble(textY.getText().toString()));
//                }
//            }
//        });
        textY.setOnFocusChangeListener(new View.OnFocusChangeListener() {
            @Override
            public void onFocusChange(View v, boolean hasFocus) {
                if (!textX.getText().toString().trim().isEmpty() &&
                        !textY.getText().toString().trim().isEmpty()) {
                    indoorMapView.setCurrentPosition(
                            Double.parseDouble(textX.getText().toString().trim()),
                            Double.parseDouble(textY.getText().toString().trim())
                    );
                }
            }
        });

//        textX.setOnFocusChangeListener(new View.OnFocusChangeListener() {
//            @Override
//            public void onFocusChange(View v, boolean hasFocus) {
//                if (!textX.getText().equals("")) {
//                    indoorMapView.setCurrentPosition(Double.parseDouble(textX.getText().toString()), Double.parseDouble(textY.getText().toString()));
//                }
//            }
//        });
        textX.setOnFocusChangeListener(new View.OnFocusChangeListener() {
            @Override
            public void onFocusChange(View v, boolean hasFocus) {
                if (!textX.getText().toString().trim().isEmpty() &&
                        !textY.getText().toString().trim().isEmpty()) {
                    indoorMapView.setCurrentPosition(
                            Double.parseDouble(textX.getText().toString().trim()),
                            Double.parseDouble(textY.getText().toString().trim())
                    );
                }
            }
        });


    }

    private void setBackground() {
        Intent intent = new Intent(Intent.ACTION_GET_CONTENT);
        intent.setType("image/*");
        startActivityForResult(intent, PICK_IMAGE_REQUEST);
    }


    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);

        if (requestCode == PICK_IMAGE_REQUEST && resultCode == RESULT_OK && data != null && data.getData() != null) {
            // Get the image URI from the intent
            Uri imageUri = data.getData();

            try {
                // Original Size Image
//                // Load the image using BitmapFactory
//                InputStream imageStream = getContentResolver().openInputStream(imageUri);
//                Bitmap selectedImage = BitmapFactory.decodeStream(imageStream);
//
//                // Set the background image in the IndoorMapMultipleView
//                indoorMapView.setBackground(selectedImage);

                // Resize image to full screen

                InputStream imageStream = getContentResolver().openInputStream(imageUri);
                Bitmap selectedImage = BitmapFactory.decodeStream(imageStream);

                // Resize the image to match the parent dimensions
                Bitmap resizedImage = getResizedBitmap(selectedImage, indoorMapView.getWidth(), indoorMapView.getHeight());

                // Set the background image in the IndoorMapMultipleView
                indoorMapView.setBackground(resizedImage);
            } catch (IOException e) {
                e.printStackTrace();
            }
        }
    }

    // Resize the bitmap to the specified width and height
    private Bitmap getResizedBitmap(Bitmap bitmap, int width, int height) {
        return Bitmap.createScaledBitmap(bitmap, width, height, true);
    }

    // Call this method to update the coordinates
//    private void updateCoordinates(double x, double y) {
//        indoorMapView.setCoordinates(x, y);
//    }

    private double getInputX() {
        String value = textX.getText().toString().trim();
        if (value.isEmpty()) return 0;
        return Double.parseDouble(value);
    }

    private double getInputY() {
        String value = textY.getText().toString().trim();
        if (value.isEmpty()) return 0;
        return Double.parseDouble(value);
    }

    private void updateManualPositionFromInput() {
        double x = getInputX();
        double y = getInputY();
        indoorMapView.setCurrentPosition(x, y);
    }


    private void updateCoordinates(List<PointModel> coords) {
        indoorMapView.setCoordinates(coords);
    }

//    private void predictKnn() {
//        wifiDataList = new ArrayList<>();
//        currentPredictionType = PredictionType.KNN;
//        wifiManager.startScan();
//    }
//
//    private void predictFingerKnn() {
//        wifiDataList = new ArrayList<>();
//        currentPredictionType = PredictionType.KNN_FINGER;
//        wifiManager.startScan();
//    }
//
//    private void predictFingerRf() {
//        wifiDataList = new ArrayList<>();
//        currentPredictionType = PredictionType.RF_FINGER;
//        wifiManager.startScan();
//    }
//
//    private void predictCNN() {
//        wifiDataList = new ArrayList<>();
//        currentPredictionType = PredictionType.CNN;
//        wifiManager.startScan();
//    }
//    private void predictGNN() {
//        wifiDataList = new ArrayList<>();
//        currentPredictionType = PredictionType.GNN;
//        wifiManager.startScan();
//    }
//
//    private void predictRf() {
//        wifiDataList = new ArrayList<>();
//        currentPredictionType = PredictionType.RF;
//        wifiManager.startScan();
//    }

    private void predictKnn() {
        wifiDataList = new ArrayList<>();
        currentPredictionType = PredictionType.KNN;
        wifiScannedLoop = 1;
        updateManualPositionFromInput();
        wifiManager.startScan();
    }

    private void predictFingerKnn() {
        wifiDataList = new ArrayList<>();
        currentPredictionType = PredictionType.KNN_FINGER;
        wifiScannedLoop = 1;
        updateManualPositionFromInput();
        wifiManager.startScan();
    }

    private void predictFingerRf() {
        wifiDataList = new ArrayList<>();
        currentPredictionType = PredictionType.RF_FINGER;
        wifiScannedLoop = 1;
        updateManualPositionFromInput();
        wifiManager.startScan();
    }

    private void predictCNN() {
        wifiDataList = new ArrayList<>();
        currentPredictionType = PredictionType.CNN;
        wifiScannedLoop = 1;
        updateManualPositionFromInput();
        wifiManager.startScan();
    }

    private void predictGNN() {
        wifiDataList = new ArrayList<>();
        currentPredictionType = PredictionType.GNN;
        wifiScannedLoop = 1;
        updateManualPositionFromInput();
        wifiManager.startScan();
    }

    private void predictRf() {
        wifiDataList = new ArrayList<>();
        currentPredictionType = PredictionType.RF;
        wifiScannedLoop = 1;
        updateManualPositionFromInput();
        wifiManager.startScan();
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