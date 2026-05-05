package com.example.vri;

import androidx.appcompat.app.AppCompatActivity;

import android.content.Intent;
import android.os.Bundle;
import android.view.View;

public class MainActivity extends AppCompatActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        initViews();
        initPermissions();
        initObjects();
        initListeners();
    }
    private void initListeners() {
    }

    private void initObjects() {
    }

    private void initPermissions() {
    }

    private void initViews() {
    }
    public void openSurveyActivity(View view) {
        Intent intent = new Intent(this, SurveyActivity.class);
        startActivity(intent);
    }

    public void openTrackActivity(View view) {
        Intent intent = new Intent(this, TrackActivity.class);
        startActivity(intent);
    }

    public void openSettingsActivity(View view) {
        Intent intent = new Intent(this, SettingsActivity.class);
        startActivity(intent);
    }

    public void openCreditActivity(View view) {
        Intent intent = new Intent(this, CreditActivity.class);
        startActivity(intent);
    }
}