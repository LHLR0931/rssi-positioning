package com.example.vri;

import android.content.Context;
import android.os.Bundle;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.widget.TextView;

import androidx.appcompat.app.AppCompatActivity;
import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowInsetsCompat;

public class CreditActivity extends AppCompatActivity implements SensorEventListener {

    private SensorManager sensorManager;
    private Sensor accelerometer;
    private float[] accelerometerData = new float[3];
    private float[] gyroscopeData = new float[3];
    private static final float NS2S = 1.0f / 1000000000.0f;
    private float timestamp;
    private float xPosition = 0.0f;
    private float yPosition = 0.0f;
    private TextView positionTextView;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_credit);
        sensorManager = (SensorManager) getSystemService(Context.SENSOR_SERVICE);
        accelerometer = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER);

        if (accelerometer != null) {
            sensorManager.registerListener(this, accelerometer, SensorManager.SENSOR_DELAY_NORMAL);
        }

        Sensor gyroscope = sensorManager.getDefaultSensor(Sensor.TYPE_GYROSCOPE);
        if (gyroscope != null) {
            sensorManager.registerListener(this, gyroscope, SensorManager.SENSOR_DELAY_NORMAL);
        }

        // Initialize TextView
        positionTextView = findViewById(R.id.positionTextView);
        updatePositionText();
    }

    @Override
    public void onSensorChanged(SensorEvent event) {
        if (event.sensor.getType() == Sensor.TYPE_ACCELEROMETER) {
            accelerometerData = event.values.clone();
        } else if (event.sensor.getType() == Sensor.TYPE_GYROSCOPE) {
            if (timestamp != 0) {
                final float dT = (event.timestamp - timestamp) * NS2S;
                gyroscopeData[0] = event.values[0];
                gyroscopeData[1] = event.values[1];
                gyroscopeData[2] = event.values[2];

                // Use gyroscope data for more accurate motion tracking
                // Update x and y positions based on sensor data and your algorithm
                // For simplicity, let's assume linear movement for demonstration purposes
                xPosition += accelerometerData[0] * dT * dT / 2;
                yPosition += accelerometerData[1] * dT * dT / 2;
                updatePositionText();
            }
            timestamp = event.timestamp;
        }

        // TODO: Update xPosition and yPosition in your application as needed
        // For example, you can send this data to your server or update UI elements.
    }

    @Override
    public void onAccuracyChanged(Sensor sensor, int accuracy) {
        // Not used in this example
    }

    private void updatePositionText() {
        // Display the X and Y positions in the TextView
        String positionText = String.format("X: %.2f, Y: %.2f", xPosition, yPosition);
        positionTextView.setText(positionText);
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        // Unregister the sensor listener to avoid memory leaks
        sensorManager.unregisterListener(this);
    }
}