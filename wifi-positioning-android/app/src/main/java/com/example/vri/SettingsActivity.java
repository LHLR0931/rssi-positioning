package com.example.vri;


import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.Nullable;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowInsetsCompat;

import com.example.vri.models.ApiResponseModel;
import com.example.vri.utils.APIHelper;
import com.example.vri.utils.Constanta;

import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;

import okhttp3.OkHttpClient;
import okhttp3.ResponseBody;
import okhttp3.logging.HttpLoggingInterceptor;
import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;
import retrofit2.Retrofit;
import retrofit2.converter.gson.GsonConverterFactory;
import android.app.DownloadManager;
import android.content.Context;
import android.net.Uri;
import android.os.Environment;

public class SettingsActivity extends AppCompatActivity {

    private APIHelper apiHelper;
    private static final int IMPORT_REQUEST_CODE = 1;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_settings);
        Button btnImport = findViewById(R.id.btnImport);
        Button btnExport = findViewById(R.id.btnExport);
        Button btnSplitData = findViewById(R.id.btnSplitData);
        TextView splitResultText = findViewById(R.id.splitResultText);

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

        btnSplitData.setOnClickListener(view -> {
            btnSplitData.setEnabled(false);
            splitResultText.setText("Splitting…");
            Call<ApiResponseModel<Object>> call = apiHelper.splitWifiData();
            call.enqueue(new Callback<ApiResponseModel<Object>>() {
                @Override
                public void onResponse(Call<ApiResponseModel<Object>> call, Response<ApiResponseModel<Object>> response) {
                    btnSplitData.setEnabled(true);
                    if (!response.isSuccessful()) {
                        splitResultText.setText("Error: " + response.code());
                        return;
                    }
                    ApiResponseModel body = response.body();
                    if (body != null) {
                        splitResultText.setText(body.getMessage() + "\n" + body.getData());
                    }
                    Toast.makeText(SettingsActivity.this, "Split complete", Toast.LENGTH_SHORT).show();
                }
                @Override
                public void onFailure(Call<ApiResponseModel<Object>> call, Throwable t) {
                    btnSplitData.setEnabled(true);
                    splitResultText.setText("Failed: " + t.getMessage());
                }
            });
        });

        btnImport.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View view) {
                // Open file picker for import
                Intent intent = new Intent(Intent.ACTION_GET_CONTENT);
                intent.setType("*/*");
                startActivityForResult(intent, IMPORT_REQUEST_CODE);
            }
        });

        btnExport.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View view) {
//                DownloadManager downloadManager = (DownloadManager) getSystemService(Context.DOWNLOAD_SERVICE);
//
//                Uri uri = Uri.fromFile(new Constanta().apiUrl+"");
//
//                DownloadManager.Request request = new DownloadManager.Request(uri);
//                request.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
//                request.setDestinationInExternalFilesDir(this, Environment.DIRECTORY_DOWNLOADS, file.getName());
//
//                // Enqueue the download request
//                long downloadId = downloadManager.enqueue(request);
                // Sample export data
//                String exportData = "Sample data to export";
//
//                Call<ResponseBody> call = apiHelper.exportWifiData();
//                call.enqueue(new Callback<ResponseBody>() {
//                    @Override
//                    public void onResponse(Call<ResponseBody> call, Response<ResponseBody> response) {
//                        if (response.isSuccessful()) {
////                            saveJsonToFile(response.body());
//                            saveJsonToFileAndNotify(response.body());
//                            // Handle the exported file data using response.body()
//                            // Note: This example assumes that the server returns the file as a binary response.
//                            // You may need to save the file or perform further processing based on your requirements.
//                        } else {
//                            // Handle error
//                        }
//                    }
//
//                    @Override
//                    public void onFailure(Call<ResponseBody> call, Throwable t) {
//                        // Handle failure
//                    }
//                });
//                // TODO: Save 'exportData' to a file (e.g., in internal or external storage)
//                // For simplicity, you can display a Toast message here.
////                Toast.makeText(SettingsActivity.this, "Data exported successfully", Toast.LENGTH_SHORT).show();
            }
        });
    }
    private void saveJsonToFile(ResponseBody responseBody) {
        try {
            // Get the input stream from the response body
            InputStream inputStream = responseBody.byteStream();

            // Create a file to save the JSON data
            File file = new File(getExternalFilesDir(null), "exported_data.json");

            // Write the data to the file
            FileOutputStream fileOutputStream = new FileOutputStream(file);
            byte[] buffer = new byte[4096];
            int bytesRead;

            while ((bytesRead = inputStream.read(buffer)) != -1) {
                fileOutputStream.write(buffer, 0, bytesRead);
            }

            fileOutputStream.close();
            inputStream.close();

            // Now, 'file' contains the exported JSON data
            // You can use 'file' as needed, for example, display a success message or open the file.

        } catch (IOException e) {
            e.printStackTrace();
            // Handle IO exception
        }
    }


    private void saveJsonToFileAndNotify(ResponseBody responseBody) {
        try {
            // Get the input stream from the response body
            InputStream inputStream = responseBody.byteStream();

            // Create a file to save the JSON data
            File file = new File(getExternalFilesDir(null), "exported_data.json");

            // Write the data to the file
            FileOutputStream fileOutputStream = new FileOutputStream(file);
            byte[] buffer = new byte[4096];
            int bytesRead;

            while ((bytesRead = inputStream.read(buffer)) != -1) {
                fileOutputStream.write(buffer, 0, bytesRead);
            }

            fileOutputStream.close();
            inputStream.close();

            // Notify the user that the file has been downloaded
            notifyFileDownloaded(file);

        } catch (IOException e) {
            e.printStackTrace();
            // Handle IO exception
        }
    }

    private void notifyFileDownloaded(File file) {
        // Use DownloadManager to notify the system about the downloaded file
        DownloadManager downloadManager = (DownloadManager) getSystemService(Context.DOWNLOAD_SERVICE);

        Uri uri = Uri.fromFile(file);

        DownloadManager.Request request = new DownloadManager.Request(uri);
        request.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
        request.setDestinationInExternalFilesDir(this, Environment.DIRECTORY_DOWNLOADS, file.getName());

        // Enqueue the download request
        long downloadId = downloadManager.enqueue(request);

        // Optionally, you can display a toast message to inform the user
//        Toast.makeText(this, "File downloaded. Check your Downloads folder.", Toast.LENGTH_SHORT).show();
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, @Nullable Intent data) {
        super.onActivityResult(requestCode, resultCode, data);

        if (requestCode == IMPORT_REQUEST_CODE && resultCode == RESULT_OK) {
            // TODO: Handle the imported file
            // 'data.getData()' contains the URI of the selected file.
            // You can read the file content using InputStream, BufferedReader, etc.
            Toast.makeText(this, "File imported successfully", Toast.LENGTH_SHORT).show();
        }
    }
}